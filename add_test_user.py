"""Insert a mock Tech subscriber for testing notifier.py."""

import database as db

TEST_PHONE = "+17845550123"
TEST_CATEGORY = "Tech"


def main() -> None:
    result = db.add_subscription(TEST_PHONE, TEST_CATEGORY)
    print(result["message"])
    print(f"  Phone:    {result['phone']}")
    print(f"  Category: {result['category']}")
    print("\nRun: python notifier.py")


if __name__ == "__main__":
    main()
