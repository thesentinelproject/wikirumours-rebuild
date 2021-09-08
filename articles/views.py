from django.shortcuts import render, get_object_or_404
# Create your views here.
from report.models import Domain, BlogPage


def index(request):
    host = request.get_host()
    domain = Domain.objects.filter(domain=host).first()

    blog_pages = BlogPage.objects.filter(visible_to_domains=domain)

    context = {
        'blog_pages': blog_pages
    }
    return render(request, "report/blogs_list.html", context)


def blog_page(request, content_slug):
    blog_page = get_object_or_404(BlogPage, content_slug=content_slug)
    return render(request, 'report/content_page.html', context={'cms_page': blog_page})
