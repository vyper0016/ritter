from pydantic import BaseModel


class User(BaseModel):
    id: int
    username: str
    name: str
    is_admin: bool
    default_participant_ids: list[int]
    profile_picture_path: str | None = None
    profile_picture_filename: str | None = None
    profile_picture_mimetype: str | None = None

    model_config = {"from_attributes": True}
