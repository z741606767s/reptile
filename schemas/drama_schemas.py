from pydantic import BaseModel, Field, HttpUrl
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


# 基础模型 - 包含公共字段
class DramaBase(BaseModel):
    category_id: int = Field(..., description="分类ID")
    title: str = Field(..., max_length=255, description="剧名称")
    desc: str = Field(..., max_length=255, description="简介")
    premiere: date = Field(..., description="首映时间")
    remark: str = Field(..., max_length=120, description="备注")
    site: str = Field(..., max_length=50, description="站点")


# 创建模型 - 用于新增数据
class DramaCreate(DramaBase):
    cover: HttpUrl = Field(..., description="封面图")
    score: Decimal = Field(
        default=Decimal("0.0"),
        max_digits=10,
        decimal_places=1,
        ge=0,
        le=10,
        description="豆瓣评分"
    )
    hot: int = Field(default=0, ge=0, description="最热")
    douban_film_review: str = Field(..., max_length=160, description="豆瓣影评")
    douyin_film_review: str = Field(..., max_length=160, description="抖音影评")
    xinlang_film_review: str = Field(..., max_length=160, description="新浪影评")
    kuaishou_film_review: str = Field(..., max_length=160, description="快手影评")
    baidu_film_review: str = Field(..., max_length=160, description="百度影评")
    url: HttpUrl = Field(..., description="绝对URL")
    href: str = Field(..., max_length=255, description="链接")


# 更新模型 - 用于部分更新数据
class DramaUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="剧名称")
    desc: Optional[str] = Field(None, max_length=255, description="简介")
    premiere: Optional[date] = Field(None, description="首映时间")
    remark: Optional[str] = Field(None, max_length=120, description="备注")
    cover: Optional[HttpUrl] = Field(None, description="封面图")
    score: Optional[Decimal] = Field(
        None,
        max_digits=10,
        decimal_places=1,
        ge=0,
        le=10,
        description="豆瓣评分"
    )
    hot: Optional[int] = Field(None, ge=0, description="最热")
    douban_film_review: Optional[str] = Field(None, max_length=160, description="豆瓣影评")
    douyin_film_review: Optional[str] = Field(None, max_length=160, description="抖音影评")
    xinlang_film_review: Optional[str] = Field(None, max_length=160, description="新浪影评")
    kuaishou_film_review: Optional[str] = Field(None, max_length=160, description="快手影评")
    baidu_film_review: Optional[str] = Field(None, max_length=160, description="百度影评")
    site: Optional[str] = Field(None, max_length=50, description="站点")
    url: Optional[HttpUrl] = Field(None, description="绝对URL")
    href: Optional[str] = Field(None, max_length=255, description="链接")


# 数据库模型 - 包含数据库自动生成的字段
class DramaInDBBase(DramaBase):
    id: int = Field(..., description="剧ID")
    cover: HttpUrl = Field(..., description="封面图")
    score: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=1,
        ge=0,
        le=10,
        description="豆瓣评分"
    )
    hot: int = Field(..., ge=0, description="最热")
    douban_film_review: str = Field(..., description="豆瓣影评")
    douyin_film_review: str = Field(..., description="抖音影评")
    xinlang_film_review: str = Field(..., description="新浪影评")
    kuaishou_film_review: str = Field(..., description="快手影评")
    baidu_film_review: str = Field(..., description="百度影评")
    url: HttpUrl = Field(..., description="绝对URL")
    href: str = Field(..., description="链接")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }


# 响应模型 - 用于返回单条数据
class Drama(DramaInDBBase):
    pass


# 列表响应模型 - 用于返回多条数据
class DramaList(BaseModel):
    total: int = Field(..., description="总记录数")
    items: List[Drama] = Field(..., description="剧列表数据")


# 简要信息模型 - 用于列表展示等场景
class DramaBrief(BaseModel):
    id: int = Field(..., description="剧ID")
    category_id: int = Field(..., description="分类ID")
    title: str = Field(..., description="剧名称")
    cover: HttpUrl = Field(..., description="封面图")
    score: Decimal = Field(
        ...,
        max_digits=10,
        decimal_places=1,
        ge=0,
        le=10,
        description="豆瓣评分"
    )
    premiere: date = Field(..., description="首映时间")
    site: str = Field(..., description="站点")

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }
