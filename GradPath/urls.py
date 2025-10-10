"""GradeTeach项目的URL配置。
此文件是项目的主URL配置文件，负责将URL请求分发到各个应用。
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from students.views import root_view

# URL模式列表
urlpatterns = [
    # Django管理后台的URL
    path('admin/', admin.site.urls),
    path('student/', include('students.urls')),  # 学生相关URL
    path('counselor/', include('counselors.urls')),  # 辅导员相关URL
    path('', root_view, name='root'),
]

# 在开发模式下，添加处理媒体文件（MEDIA_ROOT）的URL
# 这使得在开发服务器上可以通过MEDIA_URL访问上传的文件
# 注意：这不适用于生产环境！
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)