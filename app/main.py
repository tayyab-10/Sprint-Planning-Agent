# --- TEMP FIX for Python 3.13 + FastAPI + Pydantic bug ---
import typing

# Some combinations of Python (3.13) and pydantic call
# typing.ForwardRef._evaluate with either a positional 3rd arg or a
# keyword-only `recursive_guard`. To handle both safely we install a
# wrapper that accepts either form and delegates to typing._eval_type.
try:
    ForwardRef = typing.ForwardRef
except AttributeError:
    ForwardRef = None

if ForwardRef is not None:
    # keep original around just in case
    _orig_eval = getattr(ForwardRef, "_evaluate", None)

    def _evaluate_wrapper(self, globalns, localns, *args, **kwargs):
        """Evaluate a ForwardRef safely without calling typing._eval_type to avoid
        re-entrancy recursion. We try a simple eval of the forward argument in the
        provided namespaces, and fall back to the original _evaluate if present.
        """
        # Try a direct eval of the forward-ref string in the given namespaces.
        try:
            fwd = getattr(self, "__forward_arg__", None) or getattr(self, "__forward_arg", None)
            if isinstance(fwd, str):
                return eval(fwd, globalns or {}, localns or {})
        except Exception:
            # swallow and fall through to original
            pass

        # If direct eval didn't work, try the original implementation if available.
        if _orig_eval is not None:
            return _orig_eval(self, globalns, localns, *args, **kwargs)

        # As a last resort raise a TypeError similar to original behavior.
        raise TypeError("Unable to evaluate ForwardRef")

    # Replace unconditionally to ensure consistent behavior
    ForwardRef._evaluate = _evaluate_wrapper

# ---------------------------------------------------------


from fastapi import FastAPI
from app.routes.sprint_routes import router as sprint_router

app = FastAPI(title="NEXA Sprint Planner Agent")

app.include_router(sprint_router, prefix="/api/sprint", tags=["Sprint Planner"])

@app.get("/")
async def root():
    return {"message": "Sprint Planner Agent is active 🚀"}
