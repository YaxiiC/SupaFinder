"""Internationalization (i18n) support for SupaFinder."""

from typing import Dict

# Translation dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App title and description
        "app_title": "SupaFinder",
        "app_subtitle": "AI-assisted PhD supervisor discovery",
        "app_footer": "SupaFinder • AI-powered PhD supervisor discovery",
        
        # Sidebar
        "sidebar_account": "🔐 Account",
        "sidebar_logged_in": "Logged in as:",
        "sidebar_developer_mode": "🔧 **Developer Mode** - Unlimited access",
        "sidebar_beta_user": "🧪 **Beta User**",
        "sidebar_beta_searches_remaining": "free searches remaining",
        "sidebar_beta_searches_used": "Free searches used up",
        "sidebar_subscription": "📊 Subscription",
        "sidebar_plan": "Plan:",
        "sidebar_searches_remaining": "Searches remaining:",
        "sidebar_searches_this_month": "Searches this month:",
        "sidebar_upgrade": "💳 Upgrade Plan",
        "sidebar_logout": "🚪 Logout",
        "sidebar_login": "🔑 Login",
        "sidebar_register": "📝 Register",
        "sidebar_language": "🌐 Language",
        
        # Login/Register
        "login_title": "Login",
        "register_title": "Register",
        "email_label": "Email",
        "password_label": "Password",
        "confirm_password_label": "Confirm Password",
        "login_button": "Login",
        "register_button": "Register",
        "login_success": "Logged in successfully!",
        "register_success": "Registration successful! Please log in.",
        "login_error": "Invalid email or password",
        "register_error": "Registration failed",
        "password_mismatch": "Passwords do not match",
        "password_too_short": "Password must be at least 8 characters",
        "email_required": "Email is required",
        "password_required": "Password is required",
        
        # Main interface
        "main_warning_login": "⚠️ Please log in using the sidebar to use the service. First-time users get 1 free search!",
        "cv_section": "📄 Your CV (Optional)",
        "cv_caption": "You can upload a CV, enter keywords, or both",
        "cv_upload": "Upload your CV (PDF or TXT)",
        "cv_help": "Optional: Upload your CV to extract research interests automatically",
        "keywords_section": "🔬 Research Keywords (Optional)",
        "keywords_label": "Enter your research keywords (comma-separated)",
        "keywords_placeholder": "e.g., psychology, social sciences, behavioral sciences, cognitive sciences, human development, developmental psychology",
        "keywords_help": "Optional: Enter your research keywords. At least one of CV or keywords is required.",
        "universities_section": "🏛️ Universities",
        "universities_info": "Using built-in universities list (QS Rank Top 200+ universities worldwide)",
        "filters_section": "🎯 Filters",
        "regions_label": "Regions (comma-separated)",
        "regions_placeholder": "e.g., Europe, North America, Asia",
        "countries_label": "Countries (comma-separated)",
        "countries_placeholder": "e.g., Singapore, Sweden, United Kingdom",
        "qs_min_label": "Min QS Rank",
        "qs_min_help": "Minimum QS World University Ranking",
        "qs_max_label": "Max QS Rank",
        "qs_max_help": "Maximum QS World University Ranking",
        "target_label": "Target Supervisors",
        "local_db_label": "Use local DB first (recommended)",
        "search_button": "🚀 Find Supervisors",
        "login_required": "Please log in first using the sidebar",
        "cv_or_keywords_required": "Please upload a CV or enter research keywords (at least one is required)",
        
        # Search progress
        "search_stopped": "⏹️ Search stopped by user. Found {count} supervisors.",
        "search_stopped_no_results": "⏹️ Search was stopped. You can export the results found so far.",
        "search_completed": "✅ Pipeline completed successfully!",
        "stop_search_button": "⏹️ Stop Search",
        "export_results": "📥 Export Results",
        "download_results": "📥 Download Results (Excel) - {count} supervisors",
        "no_results": "No supervisors found.",
        "stopping_search": "Stopping search... Please wait for current step to finish.",
        
        # Subscription page
        "subscription_title": "💳 Subscription Plans",
        "subscription_current": "Current Plan:",
        "subscription_upgrade": "Upgrade to get more searches",
        "subscription_free": "Free",
        "subscription_personal": "Personal",
        "subscription_enterprise": "Enterprise",
        "subscription_searches_per_month": "searches per month",
        "subscription_price": "Price:",
        "subscription_features": "Features:",
        "subscription_select": "Select Plan",
        
        # Error messages
        "error_pipeline": "Error running pipeline:",
        "error_subscription": "Subscription error",
        "error_payment": "Payment processing error:",
        
        # History page
        "history_title": "📜 Search History",
        "history_no_searches": "No search history yet.",
        "history_back": "← Back to Search",
    },
    "zh": {
        # App title and description
        "app_title": "SupaFinder",
        "app_subtitle": "AI辅助的博士导师发现",
        "app_footer": "SupaFinder • AI驱动的博士导师发现",
        
        # Sidebar
        "sidebar_account": "🔐 账户",
        "sidebar_logged_in": "已登录：",
        "sidebar_developer_mode": "🔧 **开发者模式** - 无限访问",
        "sidebar_beta_user": "🧪 **测试用户**",
        "sidebar_beta_searches_remaining": "次免费搜索剩余",
        "sidebar_beta_searches_used": "免费搜索已用完",
        "sidebar_subscription": "📊 订阅",
        "sidebar_plan": "计划：",
        "sidebar_searches_remaining": "剩余搜索次数：",
        "sidebar_searches_this_month": "本月搜索次数：",
        "sidebar_upgrade": "💳 升级计划",
        "sidebar_logout": "🚪 退出登录",
        "sidebar_login": "🔑 登录",
        "sidebar_register": "📝 注册",
        "sidebar_language": "🌐 语言",
        
        # Login/Register
        "login_title": "登录",
        "register_title": "注册",
        "email_label": "邮箱",
        "password_label": "密码",
        "confirm_password_label": "确认密码",
        "login_button": "登录",
        "register_button": "注册",
        "login_success": "登录成功！",
        "register_success": "注册成功！请登录。",
        "login_error": "邮箱或密码错误",
        "register_error": "注册失败",
        "password_mismatch": "密码不匹配",
        "password_too_short": "密码至少需要8个字符",
        "email_required": "请输入邮箱",
        "password_required": "请输入密码",
        
        # Main interface
        "main_warning_login": "⚠️ 请使用侧边栏登录以使用服务。首次用户可获得1次免费搜索！",
        "cv_section": "📄 您的简历（可选）",
        "cv_caption": "您可以上传简历、输入关键词，或两者都提供",
        "cv_upload": "上传您的简历（PDF或TXT）",
        "cv_help": "可选：上传您的简历以自动提取研究兴趣",
        "keywords_section": "🔬 研究关键词（可选）",
        "keywords_label": "输入您的研究关键词（逗号分隔）",
        "keywords_placeholder": "例如：心理学、社会科学、行为科学、认知科学、人类发展、发展心理学",
        "keywords_help": "可选：输入您的研究关键词。至少需要提供简历或关键词之一。",
        "universities_section": "🏛️ 大学",
        "universities_info": "使用内置大学列表（QS排名全球前200+大学）",
        "filters_section": "🎯 筛选条件",
        "regions_label": "地区（逗号分隔）",
        "regions_placeholder": "例如：欧洲、北美、亚洲",
        "countries_label": "国家（逗号分隔）",
        "countries_placeholder": "例如：新加坡、瑞典、英国",
        "qs_min_label": "最低QS排名",
        "qs_min_help": "最低QS世界大学排名",
        "qs_max_label": "最高QS排名",
        "qs_max_help": "最高QS世界大学排名",
        "target_label": "目标导师数量",
        "local_db_label": "优先使用本地数据库（推荐）",
        "search_button": "🚀 查找导师",
        "login_required": "请先使用侧边栏登录",
        "cv_or_keywords_required": "请上传简历或输入研究关键词（至少需要提供一项）",
        
        # Search progress
        "search_stopped": "⏹️ 搜索已停止。找到 {count} 位导师。",
        "search_stopped_no_results": "⏹️ 搜索已停止。您可以导出目前已找到的结果。",
        "search_completed": "✅ 流程完成成功！",
        "stop_search_button": "⏹️ 停止搜索",
        "export_results": "📥 导出结果",
        "download_results": "📥 下载结果 (Excel) - {count} 位导师",
        "no_results": "未找到导师。",
        "stopping_search": "正在停止搜索... 请等待当前步骤完成。",
        
        # Subscription page
        "subscription_title": "💳 订阅计划",
        "subscription_current": "当前计划：",
        "subscription_upgrade": "升级以获得更多搜索次数",
        "subscription_free": "免费",
        "subscription_personal": "个人",
        "subscription_enterprise": "企业",
        "subscription_searches_per_month": "次/月",
        "subscription_price": "价格：",
        "subscription_features": "功能：",
        "subscription_select": "选择计划",
        
        # Error messages
        "error_pipeline": "运行流程时出错：",
        "error_subscription": "订阅错误",
        "error_payment": "支付处理错误：",
        
        # History page
        "history_title": "📜 搜索历史",
        "history_no_searches": "暂无搜索历史。",
        "history_back": "← 返回搜索",
    }
}


def get_text(key: str, lang: str = "en") -> str:
    """
    Get translated text for a given key.
    
    Args:
        key: Translation key
        lang: Language code ("en" or "zh")
    
    Returns:
        Translated text, or the key itself if translation not found
    """
    if lang not in TRANSLATIONS:
        lang = "en"
    
    return TRANSLATIONS.get(lang, {}).get(key, key)


def get_language() -> str:
    """Get current language from session state, default to 'en'."""
    import streamlit as st
    return st.session_state.get("language", "en")


def set_language(lang: str) -> None:
    """Set current language in session state."""
    import streamlit as st
    st.session_state.language = lang


def t(key: str) -> str:
    """
    Convenience function to get translated text using current language from session state.
    
    Args:
        key: Translation key
    
    Returns:
        Translated text
    """
    lang = get_language()
    return get_text(key, lang)

