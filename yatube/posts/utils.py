from django.core.paginator import Paginator

NUM_OF_POSTS = 10


def get_page_context(posts, request):
    paginator = Paginator(posts, NUM_OF_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
