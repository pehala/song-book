"""Views for PDF app"""
from datetime import datetime

from django.utils.translation import gettext_lazy
from django_weasyprint import WeasyTemplateView

from backend.views import fetch_all_songs


class PDFSongs(WeasyTemplateView):
    """Legacy view class for exporting songs into PDF"""
    template_name = "pdf/index.html"
    pdf_attachment = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        songs = fetch_all_songs(locale=self.request.LANGUAGE_CODE)
        context['songs'] = songs
        context['sorted_songs'] = sorted(songs, key=lambda song: song.name)
        return context

    def get_pdf_filename(self):
        return '{name}-{at}.pdf'.format(
            name=gettext_lazy("songlist"),
            at=datetime.now().strftime('%Y%m%d-%H%M'),
        )
