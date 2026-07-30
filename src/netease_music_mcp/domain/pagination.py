from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PageRequest(DomainModel):
    page: int = Field(ge=1, description="One-based page number.")
    page_size: int = Field(ge=1, description="Number of items requested per page.")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageInfo(PageRequest):
    total: int = Field(ge=0)
    has_more: bool

    @classmethod
    def from_request(cls, request: PageRequest, total: int) -> "PageInfo":
        return cls(
            page=request.page,
            page_size=request.page_size,
            total=total,
            has_more=request.offset + request.page_size < total,
        )
