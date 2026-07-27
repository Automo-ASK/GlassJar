from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Decimal end-to-end in Python, plain number in JSON so the frontend keeps
# receiving `number` fields. NGN amounts at 2dp are exact in a double.
Money = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
