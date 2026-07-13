"""
    IMPORTANT:
    The following script is NOT supposed to be run in the standard dalikam environment but instead
    should be passed through to the anaconda (micromamba) environment. The programs handles this 
    automatically in settingsVM.py, so end users do not have to worry about this.
"""

try:
    import torch 

    results: str = ""

    if torch.cuda.is_available():
        results += "CUDA is available\n"
    else:
        results += "CUDA is NOT available\n"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        results += "MPS is available\n"
    else:
        results += "MPS is NOT available\n"

        results += "CPU inference is available"

    print(results)
except Exception:
    print("Your environment is corrupt. Consider running 'uv run setup' to re-create it.")