from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re


class CategoryBase(BaseModel):
    """分类基础模型"""
    name: str = Field(..., max_length=120, description="分类名称")
    slug: str = Field(..., max_length=120, description="URL 别名，同级唯一")
    parent_id: Optional[int] = Field(None, description="父分类ID，NULL=顶级")
    level: int = Field(1, ge=1, le=10, description="层级，顶级=1")
    sort: int = Field(0, description="同级排序，越小越靠前")
    is_enabled: bool = Field(True, description="是否启用：True启用 False禁用")
    path: Optional[str] = Field(None, max_length=500, description="内部路径：1,12,123")
    uri_path: Optional[str] = Field(None, max_length=500, description="前端跳转路径：electronics/phone/smartphone")
    site: str = Field(..., max_length=50, description="站点")
    url: str = Field(..., max_length=255, description="绝对URL")
    href: str = Field(..., max_length=255, description="链接")

    # @validator('slug')
    # def validate_slug(cls, v):
    #     """验证slug格式"""
    #     if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
    #         raise ValueError('Slug只能包含小写字母、数字和连字符，且不能以连字符开头或结尾')
    #     return v


class CategoryCreate(CategoryBase):
    """创建分类模型"""
    pass


class CategoryUpdate(BaseModel):
    """更新分类模型"""
    name: Optional[str] = Field(None, max_length=120, description="分类名称")
    slug: Optional[str] = Field(None, max_length=120, description="URL 别名，同级唯一")
    parent_id: Optional[int] = Field(None, description="父分类ID，NULL=顶级")
    level: Optional[int] = Field(None, ge=1, le=10, description="层级，顶级=1")
    sort: Optional[int] = Field(None, description="同级排序，越小越靠前")
    is_enabled: Optional[bool] = Field(None, description="是否启用：True启用 False禁用")
    path: Optional[str] = Field(None, max_length=500, description="内部路径：1,12,123")
    uri_path: Optional[str] = Field(None, max_length=500, description="前端跳转路径：electronics/phone/smartphone")
    site: Optional[str] = Field(None, max_length=50, description="站点")
    url: Optional[str] = Field(None, max_length=255, description="绝对URL")
    href: Optional[str] = Field(None, max_length=255, description="链接")


class CategoryResponse(BaseModel):
    """分类响应模型"""
    id: int = Field(..., description="分类ID")
    name: str = Field(..., max_length=120, description="分类名称")
    slug: str = Field(..., max_length=120, description="URL 别名")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    level: int = Field(..., ge=1, le=10, description="层级")
    sort: int = Field(..., description="排序")
    is_enabled: bool = Field(..., description="是否启用")
    path: Optional[str] = Field(None, max_length=500, description="内部路径")
    uri_path: Optional[str] = Field(None, max_length=500, description="前端路径")
    site: str = Field(..., max_length=50, description="站点")
    url: str = Field(..., max_length=255, description="绝对URL")
    href: str = Field(..., max_length=255, description="链接")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class CategoryTree(BaseModel):
    """分类树结构"""
    id: int = Field(..., description="分类ID")
    name: str = Field(..., max_length=120, description="分类名称")
    slug: str = Field(..., max_length=120, description="URL 别名")
    level: int = Field(..., ge=1, le=10, description="层级")
    sort: int = Field(..., description="排序")
    is_enabled: bool = Field(..., description="是否启用")
    children: List['CategoryTree'] = Field(default_factory=list, description="子分类")
