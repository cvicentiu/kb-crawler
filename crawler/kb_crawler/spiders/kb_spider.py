from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import HtmlLexer
from pygments.formatters import TerminalFormatter

import scrapy


def print_node(text):
    print('----')
    pretty = BeautifulSoup(text, 'html.parser').prettify()
    print(highlight(pretty, HtmlLexer(), TerminalFormatter()))


class KBSpider(scrapy.Spider):
    name = "kb"
    allowed_domains = ['mariadb.com']

    def start_requests(self):
        urls = [
            "https://mariadb.com/kb/en/documentation/",
            #"https://mariadb.com/kb/en/select/",
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def follow_url(self, response, url):
        full_url = response.urljoin(url)
        # TODO(cvicentiu) skip the error code pages for now.
        #if 'mariadb-error-codes' in full_url:
        #    return
        # Skip anything that's not the english version of KB.
        if 'https://mariadb.com/kb/en' not in full_url:
            return
        yield response.follow(url=full_url, callback=self.parse)

    def handle_media_listing_page(self, response, listings):
        listing_urls = listings.css('* > a:not(.media-body)::attr(href)')
        for url in listing_urls.getall():
            yield from self.follow_url(response, url)

    def handle_answer_inner_links(self, response, block):
        text_links = block.css('* > a::attr(href)').getall()
        for url in text_links:
            yield from self.follow_url(response, url)

    def parse_content_node_list(self, response, nodes):
        result = []

        for node in nodes:

            soup = BeautifulSoup(node.get(), 'html.parser')
            base_node = soup.find()
            tag = base_node.name
            inner_text = ' '.join(list(base_node.stripped_strings))
            #tag = node.xpath('name()').get()
            #inner_text = node.css('::text').get()

            suffix = ''
            if tag == 'h2':
                heading = '## '
            elif tag == 'h3':
                heading = '### '
            elif tag == 'h4':
                heading = '#### '
            elif tag == 'h5':
                heading = '##### '
            elif tag == 'h6':
                heading = '###### '
            elif tag == 'p':
                heading = ''
            elif tag == 'li':
                heading = '- '  # for now, everything is list item.
            elif tag == 'pre':
                heading = '```\n'
                suffix = '\n```'
            else:
                assert 0, tag

            result.append(f'{heading}{inner_text}{suffix}')

        result = '\n\n'.join(result)
        print(result)
        return result

    def parse(self, response):
        page_title = response.css('#content > h1::text').get()
        page_content = response.css('#content > div')

        dir_listing = page_content.css('.listing')
        if len(dir_listing):
            yield from self.handle_media_listing_page(response, dir_listing)
            # There might be some "content" after the listing, but we'll ignore
            # it for now.
            # TODO(cvicentiu) improve this later.
            return

        question_block = page_content.css('.question')
        answer_block = page_content.css('.answer')

        assert len(question_block) <= 1, f'Multi question page? {response.url}'
        assert len(answer_block) <= 1, f'Multi answer page? {response.url}'

        if len(question_block) and not len(answer_block):
            # This is a question page with no answers.
            # Skip for now.
            return

        if len(question_block) and len(answer_block):
            # This is a question page with an answer.
            # Skip for now.
            return

        if len(answer_block):
            yield from self.handle_answer_inner_links(response, answer_block)

            nodes = answer_block.css('h2, h3, h4, h5, '
                                     'h6, p, pre, li')
            content_as_md = self.parse_content_node_list(response, nodes)
            yield {
                'url': response.url,
                'title': page_title,
                'content': content_as_md
            }
            return

        assert 0, f'Unhandled page type {response.url}'
