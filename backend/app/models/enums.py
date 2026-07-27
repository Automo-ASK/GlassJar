import enum

from sqlalchemy import Enum as SAEnum


class MemberRole(str, enum.Enum):
    ADMIN = "admin"
    TREASURER = "treasurer"
    MEMBER = "member"


class CollectionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class EntryStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REVERSED = "reversed"


class PaymentChannel(str, enum.Enum):
    CHECKOUT = "checkout"
    MANUAL_CASH = "manual_cash"
    MANUAL_TRANSFER = "manual_transfer"


class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    AWAITING_OTP = "awaiting_otp"
    PAID_OUT = "paid_out"
    FAILED = "failed"


class LedgerEntryType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


def db_enum(enum_cls: type[enum.Enum]) -> SAEnum:
    """Store enum *values* (lowercase strings) as plain VARCHAR on every dialect."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )
