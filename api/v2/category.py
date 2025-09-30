import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTree
)
from schemas.base import ResponseModel, ListResponseModel, ErrorResponseModel
from services import CategoryService
from config import settings

# 配置日志
logging.basicConfig(level=settings.LOG_LEVEL,
                    format=settings.LOG_FORMAT,
                    datefmt=settings.LOG_DATE_FORMAT)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ResponseModel, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate):
    """创建分类"""
    result = await CategoryService.create(category)
    if not result:
        return ErrorResponseModel(
            error_code="CATEGORY_CREATE_FAILED",
            error_detail="创建分类失败，可能是slug已存在"
        )

    return ResponseModel(
        message="分类创建成功",
        data=result
    )


@router.get("/", response_model=ListResponseModel)
async def read_categories(
        skip: int = Query(0, ge=0, description="跳过记录数"),
        limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
        site: Optional[str] = Query(None, description="按站点过滤"),
        is_enabled: Optional[bool] = Query(None, description="按启用状态过滤"),
        parent_id: Optional[int] = Query(None, description="按父分类ID过滤")
):
    """获取分类列表"""
    categories = await CategoryService.get_multi(
        skip=skip,
        limit=limit,
        site=site,
        is_enabled=is_enabled,
        parent_id=parent_id
    )

    return ListResponseModel(
        total=len(categories),
        page=skip // limit + 1,
        limit=limit,
        data=categories
    )

@router.get("/list", response_model=ResponseModel)
async def read_category_list(parent_id: Optional[int] = None):
    """获取分类列表"""
    logging.info(f"获取分类列表，parent_id: {parent_id}")
    data = await CategoryService.get_by_parent_id(parent_id)
    return ResponseModel(
        data=data
    )

@router.get("/{category_id}", response_model=ResponseModel)
async def read_category(category_id: int):
    """根据ID获取分类"""
    category = await CategoryService.get(category_id)
    if not category:
        return ErrorResponseModel(
            error_code="CATEGORY_NOT_FOUND",
            error_detail=f"分类ID {category_id} 不存在"
        )

    return ResponseModel(
        data=category
    )


@router.put("/{category_id}", response_model=ResponseModel)
async def update_category(category_id: int, category: CategoryUpdate):
    """更新分类"""
    result = await CategoryService.update(category_id, category)
    if not result:
        return ErrorResponseModel(
            error_code="CATEGORY_UPDATE_FAILED",
            error_detail="更新分类失败，可能是分类不存在"
        )

    return ResponseModel(
        message="分类更新成功",
        data=result
    )


@router.delete("/{category_id}", response_model=ResponseModel)
async def delete_category(category_id: int):
    """删除分类"""
    success = await CategoryService.delete(category_id)
    if not success:
        return ErrorResponseModel(
            error_code="CATEGORY_DELETE_FAILED",
            error_detail="删除分类失败，可能是分类不存在"
        )

    return ResponseModel(
        message="分类删除成功"
    )


@router.get("/{category_id}/children", response_model=ResponseModel)
async def read_category_children(category_id: int):
    """获取分类的子分类"""
    children = await CategoryService.get_children(category_id)
    return ResponseModel(
        data=children
    )


@router.get("/site/{site}/tree", response_model=ResponseModel)
async def read_category_tree(site: str, parent_id: Optional[int] = None):
    """获取分类树结构"""
    tree = await CategoryService.get_tree(site, parent_id)
    return ResponseModel(
        data=tree
    )