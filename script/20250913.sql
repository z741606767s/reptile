-- 演员表
CREATE TABLE `r_actor` (
  `id` bigint(20) unsigned zerofill NOT NULL AUTO_INCREMENT COMMENT '演员ID',
  `actor_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '演员名字',
  `cover` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '头像',
  `desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '简介',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='演员表';


-- 分类表
CREATE TABLE `r_category` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '分类名称',
  `slug` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'URL 别名，同级唯一',
  `parent_id` bigint unsigned DEFAULT NULL COMMENT '父分类ID，NULL=顶级',
  `level` tinyint(3) unsigned zerofill NOT NULL COMMENT '层级，顶级=1',
  `sort` int NOT NULL DEFAULT '0' COMMENT '同级排序，越小越靠前',
  `is_enabled` tinyint NOT NULL DEFAULT '1' COMMENT '是否启用：1启用 0禁用',
  `path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '内部路径：1,12,123',
  `uri_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '前端跳转路径：electronics/phone/smartphone',
  `site` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '站点',
  `url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '绝对URL',
  `href` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '链接',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_site_slug_parent` (`slug`,`parent_id`,`site`) USING BTREE COMMENT '业务唯一：同站点同层级同slug唯一（含顶级）',
  KEY `idx_site_path` (`path`(191),`site`) COMMENT '站点+path 查后代',
  KEY `idx_site_enabled` (`is_enabled`,`site`) COMMENT '备用过滤'
) ENGINE=InnoDB AUTO_INCREMENT=127 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='分类表';


-- 剧表
CREATE TABLE `r_darma` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '剧ID',
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '剧名称',
  `desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '简介',
  `premiere` date NOT NULL COMMENT '首映时间',
  `remark` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '备注',
  `cover` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '封面图',
  `score` decimal(10,1) unsigned NOT NULL DEFAULT '0.0' COMMENT '豆瓣评分',
  `hot` int(10) unsigned zerofill NOT NULL COMMENT '最热',
  `douban_film_review` varchar(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '豆瓣影评',
  `douyin_film_review` varchar(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '抖音影评',
  `xinlang_film_review` varchar(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '新浪影评',
  `kuaishou_film_review` varchar(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '快手影评',
  `baidu_film_review` varchar(160) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '百度影评',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_title` (`title`),
  KEY `idx_premiere` (`premiere`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='剧表';


-- 导演表
CREATE TABLE `r_direct` (
  `id` bigint(20) unsigned zerofill NOT NULL AUTO_INCREMENT COMMENT '导演ID',
  `direct_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '导演名字',
  `cover` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '头像',
  `desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '简介',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='导演表';


-- 剧-演员关联表
CREATE TABLE `r_drama_actor` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `drama_id` bigint NOT NULL COMMENT '剧ID',
  `actor_id` bigint NOT NULL COMMENT '演员ID',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='剧-演员关联表';


-- Banner表
CREATE TABLE `r_drama_banner` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `banner_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'banner图',
  `title` varchar(180) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标题',
  `tag_names` varchar(180) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'tag名称',
  `desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '简介',
  `jump_url` varchar(255) NOT NULL COMMENT '跳转地址',
  `jump_method` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '跳转方式',
  `sort` int(10) unsigned zerofill NOT NULL COMMENT '排序',
  `is_enabled` tinyint unsigned NOT NULL DEFAULT '1' COMMENT '是否启用：1启用 0禁用',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Banner表';


-- 剧-导演关联表
CREATE TABLE `r_drama_direct` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '关联ID',
  `drama_id` bigint NOT NULL COMMENT '剧ID',
  `direct_id` bigint NOT NULL COMMENT '导演ID',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='剧-导演关联表';


-- 剧集表
CREATE TABLE `r_drama_episode` (
  `id` bigint(10) unsigned zerofill NOT NULL AUTO_INCREMENT COMMENT '集ID',
  `drama_id` bigint unsigned NOT NULL COMMENT '剧ID',
  `playback_channel` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '播放渠道',
  `total_episodes` int(10) unsigned zerofill NOT NULL COMMENT '总集数',
  `episode_number` int(10) unsigned zerofill NOT NULL COMMENT '集序号',
  `episode_name` char(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '集名称',
  `play_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '播放URL',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_drama_id_channel_number` (`drama_id`,`playback_channel`,`episode_number`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='剧集表';


-- 剧标签表
CREATE TABLE `r_tag` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `name` char(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '标签名称',
  `color` char(7) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '#409EFF' COMMENT '前端色值，如 #FF5722',
  `group` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'default' COMMENT '分组（用途/场景）',
  `is_hot` tinyint(3) unsigned zerofill NOT NULL COMMENT '热门标签: 1-是 0-否',
  `sort` int(10) unsigned zerofill NOT NULL COMMENT '排序',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='剧标签表';