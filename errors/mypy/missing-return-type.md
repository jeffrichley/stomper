### Missing return type annotation (missing-return-type)

Add explicit return type annotations to functions to improve type safety and code clarity.

#### Examples:
- Add `-> ReturnType` to function signatures
- Use `-> None` for functions that don't return a value
- Use `-> list[Type]` for functions returning lists
- Use `-> Type | None` for functions that may return None

#### Fix Strategy:
- Identify what type the function returns by examining the return statements
- Add the appropriate type hint after the function parameters
- Use built-in generic types (list, dict, tuple, set) directly (Python 3.9+)
- For optional types, use `Type | None` instead of `Optional[Type]` (Python 3.10+)
- For multiple return types, use union types `TypeA | TypeB`
- Use `-> None` explicitly for procedures (functions without return value)

#### Common Patterns:
```python
# Before
def process_data(items):
    return [item.upper() for item in items]

# After
def process_data(items: list[str]) -> list[str]:
    return [item.upper() for item in items]
```

```python
# Before
def get_user(user_id):
    if user_id in users:
        return users[user_id]
    return None

# After
def get_user(user_id: int) -> User | None:
    if user_id in users:
        return users[user_id]
    return None
```

