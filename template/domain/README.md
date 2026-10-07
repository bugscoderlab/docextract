# template/domain — copy this to start a domain

The engine is domain-free. A real project = the engine + **one domain module**
like this. Copy this folder into your project and fill in the TODOs:

| File | Fill in |
|---|---|
| `schema.py` | your Pydantic output shape, with `Field(description=…)` |
| `prompt.py` | your domain rules (vocabulary, money, what to extract) |
| `record.py` | map the schema to the stored record (money → integer minor units) |
| `wire.py` | assemble a `Domain` and a router; wire your database |

Then, in your app:

```python
from domain.wire import build_domain, build_router_for

app.include_router(build_router_for(engine))   # engine = your SQLAlchemy engine
```

Do **not** put domain words into the engine package — keep them here.
