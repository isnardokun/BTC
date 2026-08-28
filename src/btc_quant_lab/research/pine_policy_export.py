from __future__ import annotations

import ast

from btc_quant_lab.ai.sandbox import validate_sandbox_source
from btc_quant_lab.models import PivotConfig
from btc_quant_lab.research.pine_export import export_baseline_pine, export_baseline_strategy_pine
from btc_quant_lab.research.pine_filter_export import _CONTEXT_PREAMBLE, _FEATURE_EXPR

_SIGNAL_EXPR = {
    "direction": "bqrSignalDir",
    "top": "confirmedTop",
    "bottom": "confirmedBottom",
    "confirm_price": "close",
    "bars_to_confirm": "confirmedAge",
}

_BINOPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Div: "/",
    ast.Mod: "%",
}

_CMPOPS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
}


class PinePolicyExportError(ValueError):
    pass


def _quote(value: str) -> str:
    return '"' + value.replace('"', "'") + '"'


def _subscript_key(node: ast.Subscript) -> tuple[str, str]:
    if not isinstance(node.value, ast.Name) or node.value.id not in {"signal", "features"}:
        raise PinePolicyExportError("only signal[...] and features[...] subscripts are exportable")
    key_node = node.slice
    if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
        raise PinePolicyExportError("policy dict keys must be constant strings")
    return node.value.id, key_node.value


def _compile_membership(left: str, op: ast.cmpop, comparator: ast.AST) -> str:
    if not isinstance(comparator, (ast.List, ast.Tuple)) or not comparator.elts:
        raise PinePolicyExportError("in/not in requires a non-empty literal list or tuple")
    checks = [f"({left} == {_compile_expr(item)})" for item in comparator.elts]
    joined = " or ".join(checks)
    if isinstance(op, ast.NotIn):
        return f"not ({joined})"
    return f"({joined})"


def _compile_expr(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return "true" if node.value else "false"
        if isinstance(node.value, str):
            return _quote(node.value)
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return repr(float(node.value))
        raise PinePolicyExportError(f"constant is not exportable: {node.value!r}")

    if isinstance(node, ast.Subscript):
        namespace, key = _subscript_key(node)
        if namespace == "features":
            expr = _FEATURE_EXPR.get(key)
            if expr is None:
                raise PinePolicyExportError(f"feature is not Pine-exportable: {key}")
            return expr
        expr = _SIGNAL_EXPR.get(key)
        if expr is None:
            raise PinePolicyExportError(f"signal field is not Pine-exportable: {key}")
        return expr

    if isinstance(node, ast.BoolOp):
        op = "and" if isinstance(node.op, ast.And) else "or"
        return "(" + f" {op} ".join(_compile_expr(value) for value in node.values) + ")"

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return f"not ({_compile_expr(node.operand)})"
        if isinstance(node.op, ast.USub):
            return f"-({_compile_expr(node.operand)})"
        if isinstance(node.op, ast.UAdd):
            return f"+({_compile_expr(node.operand)})"
        raise PinePolicyExportError(f"unary operator is not exportable: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise PinePolicyExportError(f"binary operator is not exportable: {type(node.op).__name__}")
        return f"({_compile_expr(node.left)} {op} {_compile_expr(node.right)})"

    if isinstance(node, ast.IfExp):
        return (
            f"({_compile_expr(node.test)} ? {_compile_expr(node.body)} : "
            f"{_compile_expr(node.orelse)})"
        )

    if isinstance(node, ast.Compare):
        left_node = node.left
        parts: list[str] = []
        for op, right_node in zip(node.ops, node.comparators, strict=True):
            left = _compile_expr(left_node)
            if isinstance(op, (ast.In, ast.NotIn)):
                parts.append(_compile_membership(left, op, right_node))
            else:
                token = _CMPOPS.get(type(op))
                if token is None:
                    raise PinePolicyExportError(
                        f"comparison operator is not exportable: {type(op).__name__}"
                    )
                parts.append(f"({left} {token} {_compile_expr(right_node)})")
            left_node = right_node
        return parts[0] if len(parts) == 1 else "(" + " and ".join(parts) + ")"

    if isinstance(node, ast.Name):
        raise PinePolicyExportError(
            f"local variable '{node.id}' is not supported by the first Pine policy exporter"
        )

    raise PinePolicyExportError(f"expression is not Pine-exportable: {type(node).__name__}")


def _compile_sequence(statements: list[ast.stmt]) -> str:
    if not statements:
        raise PinePolicyExportError("every policy path must return a boolean expression")
    first, *rest = statements

    if isinstance(first, ast.Return):
        if first.value is None:
            raise PinePolicyExportError("bare return is not exportable")
        if rest:
            raise PinePolicyExportError("unreachable statements after return are not allowed")
        return _compile_expr(first.value)

    if isinstance(first, ast.If):
        true_branch = _compile_sequence([*first.body, *rest])
        false_branch = _compile_sequence([*first.orelse, *rest])
        return f"({_compile_expr(first.test)} ? {true_branch} : {false_branch})"

    if isinstance(first, ast.Assign):
        raise PinePolicyExportError(
            "local assignments are valid in the runtime sandbox but are not yet Pine-exportable"
        )

    raise PinePolicyExportError(f"statement is not Pine-exportable: {type(first).__name__}")


def compile_policy_to_pine_expression(source: str) -> str:
    """Compile a restricted pure-return policy to one Pine boolean expression."""
    validate_sandbox_source(source)
    tree = ast.parse(source, mode="exec")
    fn = tree.body[0]
    if not isinstance(fn, ast.FunctionDef):
        raise PinePolicyExportError("accept_signal function was not found")
    return _compile_sequence(fn.body)


def _policy_block(expression: str) -> str:
    return f'''// Deterministic AST translation of accept_signal(signal, features).
bool bqrRawConfirmedBear = confirmedBear
bool bqrRawConfirmedBull = confirmedBull
bool bqrPolicyRejectedBear = false
bool bqrPolicyRejectedBull = false

if bqrRawConfirmedBear or bqrRawConfirmedBull
    int bqrSignalDir = bqrRawConfirmedBear ? -1 : 1
    int bqrPriorRunBars = bar_index > 0 ? (close[1] > open[1] ? bullRun : close[1] < open[1] ? bearRun : 0) : 0
    float bqrSignalRangeAtr = bqrAtr14 > 0 ? (confirmedTop - confirmedBottom) / bqrAtr14 : na

    int bqrKnownLayers = 0
    int bqrContradictionScore = 0
    if bqrTrendRegime == "bull" or bqrTrendRegime == "bear"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrTrendRegime == "bear") or (bqrSignalDir == -1 and bqrTrendRegime == "bull")
            bqrContradictionScore += 1
    if bqrMarketStructure == "bull" or bqrMarketStructure == "bear"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrMarketStructure == "bear") or (bqrSignalDir == -1 and bqrMarketStructure == "bull")
            bqrContradictionScore += 1
    if bqrStructureBreak == "bullish_bos" or bqrStructureBreak == "bearish_bos"
        bqrKnownLayers += 1
        if (bqrSignalDir == 1 and bqrStructureBreak == "bearish_bos") or (bqrSignalDir == -1 and bqrStructureBreak == "bullish_bos")
            bqrContradictionScore += 1

    string bqrSignalContext = bqrKnownLayers == 0 ? "unknown" : bqrContradictionScore == 0 ? "aligned" : bqrContradictionScore == bqrKnownLayers ? "contrarian" : "mixed"
    bool bqrPolicyAccepted = {expression}
    if not bqrPolicyAccepted
        bqrPolicyRejectedBear := bqrRawConfirmedBear
        bqrPolicyRejectedBull := bqrRawConfirmedBull
        confirmedBear := false
        confirmedBull := false

'''


def export_policy_pine(
    cfg: PivotConfig,
    policy_source: str,
    *,
    strategy: bool = False,
    title: str | None = None,
) -> str:
    """Export a pure-return AST policy plus its causal feature context to Pine v6."""
    expression = compile_policy_to_pine_expression(policy_source)
    if strategy:
        source = export_baseline_strategy_pine(
            cfg,
            title=title or "BQR Policy Reversal Strategy",
        )
        policy_marker = "// Strategy verification layer: opposite confirmation closes/reverses."
    else:
        source = export_baseline_pine(cfg, title=title or "BQR Policy Pivot")
        policy_marker = "// 2) Detect a new transition using only the prior run and the current candle."

    context_marker = "// 1) Resolve the candidate that already existed before this bar."
    if context_marker not in source or policy_marker not in source:
        raise PinePolicyExportError("unexpected baseline Pine template")

    source = source.replace(context_marker, _CONTEXT_PREAMBLE + context_marker, 1)
    source = source.replace(policy_marker, _policy_block(expression) + policy_marker, 1)
    source += '''
plotshape(bqrPolicyRejectedBear, title="BQR policy rechazó pivote bajista", style=shape.xcross, location=location.abovebar, color=color.gray, size=size.tiny)
plotshape(bqrPolicyRejectedBull, title="BQR policy rechazó pivote alcista", style=shape.xcross, location=location.belowbar, color=color.gray, size=size.tiny)
'''
    return source
