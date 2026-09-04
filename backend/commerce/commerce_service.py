from abc import ABC, abstractmethod


class CommerceService(ABC):
    """Abstraction the agents/growth-engine talk to. Agents never touch
    the database directly — everything goes through here."""

    @abstractmethod
    async def search_products(self, category: str, max_price: float, filters: dict) -> list[dict]:
        ...

    @abstractmethod
    async def get_product(self, product_id: str) -> dict:
        ...

    @abstractmethod
    async def check_inventory(self, product_id: str) -> int:
        ...

    @abstractmethod
    async def create_cart(self, product_id: str, quantity: int) -> dict:
        ...

    @abstractmethod
    async def get_cart(self, cart_id: str) -> dict:
        ...

    @abstractmethod
    async def add_line_item(self, cart_id: str, product_id: str, quantity: int) -> dict:
        ...

    @abstractmethod
    async def set_shipping_address(self, cart_id: str, address: dict) -> dict:
        ...

    @abstractmethod
    async def complete_cart(self, cart_id: str) -> dict:
        ...