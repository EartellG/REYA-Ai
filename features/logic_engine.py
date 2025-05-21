from sympy import symbols, simplify_logic, sympify
from sympy.logic.boolalg import And, Or, Not

def evaluate_expression(expression: str):
    try:
        simplified = simplify_logic(sympify(expression))
        return str(simplified)
    except Exception as e:
        return f"Error evaluating logic: {e}"

def evaluate_logic(text):
    """
    Wrapper function to process user input and pass logical expressions to SymPy.
    Tries to detect if input looks like a logical expression.
    """
    try:
        result = evaluate_expression(text)
        return f"The simplified logic is: {result}"
    except Exception as e:
        return f"I couldn’t evaluate that logic. Error: {e}"
