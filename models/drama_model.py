from pydantic import Field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import field_serializer
from models.base import BaseModelMixin

class DramaModel(BaseModelMixin):
    """剧表数据模型，对应数据库中的 r_drama 表"""
    id: Optional[int] = Field(None, description="剧ID，自增主键")
    category_id: int = Field(..., description="分类ID")
    title: str = Field(..., max_length=255, description="剧名称")
    desc: str = Field(..., max_length=255, description="简介")
    premiere: date = Field(..., description="首映时间")
    remark: str = Field(..., max_length=120, description="备注")
    cover: str = Field(..., max_length=255, description="封面图URL")
    score: Decimal = Field(
        default=Decimal("0.0"),
        max_digits=10,
        decimal_places=1,
        ge=0,
        description="豆瓣评分"
    )
    hot: int = Field(default=0, ge=0, description="热度值")
    douban_film_review: str = Field(..., max_length=160, description="豆瓣影评")
    douyin_film_review: str = Field(..., max_length=160, description="抖音影评")
    xinlang_film_review: str = Field(..., max_length=160, description="新浪影评")
    kuaishou_film_review: str = Field(..., max_length=160, description="快手影评")
    baidu_film_review: str = Field(..., max_length=160, description="百度影评")
    site: str = Field(..., max_length=50, description="站点名称")
    url: str = Field(..., max_length=255, description="绝对URL")
    href: str = Field(..., max_length=255, description="链接")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: Optional[datetime], _info: Any) -> Optional[str]:
        """将 datetime 对象序列化为指定格式的字符串"""
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    class Config:
        """模型配置类"""
        from_attributes = True  # 支持从ORM对象创建模型
        json_encoders = {
            Decimal: lambda v: float(v)  # 将Decimal类型转换为float以便JSON序列化
        }
        table_name = "r_drama"

