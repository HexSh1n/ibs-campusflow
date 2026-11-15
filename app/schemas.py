from typing import Literal

from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    login: str
    displayName: str
    role: Literal["student", "admin"]


class LoginResponse(BaseModel):
    token: str
    user: UserSchema


class RoomSchema(BaseModel):
    id: int
    name: str
    building: Literal["A", "B", "C", "D"]
    floor: int
    capacity: int
    equipment: list[str]


class FreeSlotSchema(BaseModel):
    startTime: str
    endTime: str


class FreeSlotsResponse(BaseModel):
    roomId: int
    date: str
    freeSlots: list[FreeSlotSchema]


class BookingSchema(BaseModel):
    id: int
    roomId: int
    roomName: str
    userId: int
    userDisplayName: str
    date: str
    startTime: str
    endTime: str
    status: Literal["active", "cancelled"]
    comment: str


class BookingCancelResponse(BaseModel):
    id: int
    status: Literal["cancelled"]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict
