"""Seed the knowledge base with common error solutions."""

SEED_DATA = [
    {
        "error": "ModuleNotFoundError: No module named 'xyz'",
        "solution": "Install the missing module with `pip install xyz`. "
                    "If using a virtual environment, ensure it is activated.",
        "source": "knowledge_base",
    },
    {
        "error": "ImportError: cannot import name 'foo' from 'bar'",
        "solution": "Verify the module exports the name. Check for circular imports. "
                    "Ensure the correct module is installed and the import path is accurate.",
        "source": "knowledge_base",
    },
    {
        "error": "KeyError: 'some_key'",
        "solution": "Use `.get(key, default)` to safely access dict keys. "
                    "Check if the key exists with `key in dict` before access.",
        "source": "knowledge_base",
    },
    {
        "error": "IndexError: list index out of range",
        "solution": "Ensure the index is within `0` and `len(list) - 1`. "
                    "Check that the list is not empty before accessing elements.",
        "source": "knowledge_base",
    },
    {
        "error": "TypeError: 'NoneType' object is not callable",
        "solution": "Assign the result of the function call to a variable instead of "
                    "overwriting the function name. Verify no variable shadows the function.",
        "source": "knowledge_base",
    },
    {
        "error": "FileNotFoundError: [Errno 2] No such file or directory",
        "solution": "Double-check the file path. Use `os.path.exists()` to verify. "
                    "Use `pathlib.Path` for cross-platform path handling.",
        "source": "knowledge_base",
    },
    {
        "error": "ValueError: invalid literal for int() with base 10",
        "solution": "Ensure the string contains only digits. Use `str.isdigit()` to validate "
                    "before conversion. Handle with try/except.",
        "source": "knowledge_base",
    },
    {
        "error": "AttributeError: 'NoneType' object has no attribute 'foo'",
        "solution": "The variable is None when you try to access an attribute. "
                    "Add a None check before access or use a default value.",
        "source": "knowledge_base",
    },
    {
        "error": "ConnectionRefusedError: [Errno 61] Connection refused",
        "solution": "Ensure the server is running and the port is correct. "
                    "Check firewall settings. Use `netstat` or `lsof` to verify the port is listening.",
        "source": "knowledge_base",
    },
    {
        "error": "SyntaxError: invalid syntax",
        "solution": "Check for missing colons, unmatched parentheses, or incorrect indentation. "
                    "Use a linter like `flake8` or `ruff` to catch syntax issues early.",
        "source": "knowledge_base",
    },
    {
        "error": "PermissionError: [Errno 13] Permission denied",
        "solution": "Check file permissions. On Linux/macOS use `chmod`. "
                    "On Windows, ensure the file is not open in another program. "
                    "Run with appropriate privileges.",
        "source": "knowledge_base",
    },
    {
        "error": "RecursionError: maximum recursion depth exceeded",
        "solution": "Add a base case to your recursive function. "
                    "Consider rewriting the algorithm iteratively. "
                    "Increase recursion limit with `sys.setrecursionlimit()` as a temporary fix.",
        "source": "knowledge_base",
    },
]


def get_seed_documents():
    texts = []
    metadatas = []
    for item in SEED_DATA:
        texts.append(f"Error: {item['error']}\nSolution: {item['solution']}")
        metadatas.append({"source": item["source"], "error": item["error"]})
    return texts, metadatas


if __name__ == "__main__":
    from db.chroma import ChromaClient
    client = ChromaClient()
    texts, metadatas = get_seed_documents()
    client.add_documents(texts, metadatas)
    print(f"Seeded {len(texts)} documents into ChromaDB.")
