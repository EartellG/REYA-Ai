from sympy import symbols, simplify_logic, sympify
from sympy.logic.boolalg import And, Or, Not

def evaluate_expression(expression: str):
    try:
        simplified = simplify_logic(sympify(expression))
        return str(simplified)
    except Exception as e:
        return f"Error evaluating logic: {e}"
