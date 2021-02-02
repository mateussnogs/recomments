import scrapy
from scrapy_splash import SplashRequest
from scrapy.http import FormRequest


# models 

class ArtigoItem(scrapy.Item):
    autor = scrapy.Field()
    titulo = scrapy.Field()
    conteudo = scrapy.Field()
    data = scrapy.Field()
    nLikes = scrapy.Field()
    isComment = scrapy.Field()
    idArtigo = scrapy.Field()
    idComment = scrapy.Field()


# class CommentItem(scrapy.Item):
#     autor = scrapy.Field()
#     conteudo = scrapy.Field()
#     nLikes = scrapy.Field()

# ------------------------------------------------------------------------------------

ID = 0
ID_COMMENT = 0

class TestSpider(scrapy.Spider):
    name='test_splash'

    start_urls = ["http://www.folha.uol.com.br/colunaseblogs/#colunas-e-blogs"]

    def start_requests(self):
        for url in self.start_urls:
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(url, self.parse_colunas, args=splash_args)

    def parse_colunas(self, response):
        colunistas_urls = response.css("h3.c-author__kicker.c-author__kicker--medium a::attr(href)").getall()
        for url in colunistas_urls:
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(url, self.parse_coluna, args=splash_args)
 
    
    def parse_coluna(self, response):
        textos_urls = response.css("div.c-headline__content a::attr(href)").getall()
        
        for url in textos_urls:
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(url, self.parse_texto, args=splash_args)
        
    def parse_texto(self, response):
        global ID
        artigo = ArtigoItem()
        # artigo['conteudo'] = response.css("div.c-news__content p")
        artigo['idArtigo'] = ID
        ID += 1
        artigo['titulo'] = response.xpath("//h1[contains(@class, 'title')]").get()
        artigo['conteudo'] = response.xpath("//div[contains(@class, 'news__content')]//p").getall()
        artigo['autor'] = response.css("h4.c-top-columnist__name a::text").get()
        artigo['data'] = response.css("time[itemprop='datePublished']::text").get()
        artigo['isComment'] = False
        yield artigo
        all_coments_link = response.css("a.more.c-button::attr(href)").get()
        if (all_coments_link is not None):
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(all_coments_link, self.parse_coments, args=splash_args, cb_kwargs={'idArtigo': artigo['idArtigo']})


    def parse_coments(self, response, idArtigo):
        global ID_COMMENT
        conteudos = response.css("p.c-list-comments__comment").getall()
        autores = response.css("strong.c-list-comments__user").getall()
        likes = response.xpath("//button[contains(@class, 'rating')]/span").getall()
        coments = zip(autores, conteudos, likes)
        for c in coments:            
            coment = ArtigoItem()
            coment['conteudo'] = c[0]
            coment['autor'] = c[1]
            coment['nLikes'] = c[2]
            coment['isComment'] = True
            coment['idArtigo'] = idArtigo
            coment['idComment'] = ID_COMMENT
            ID_COMMENT+=1
            yield coment
        temProx = response.css("li.c-pagination__arrow a svg.icon.icon--chevron-right").get()
        if (temProx is not None):
            # getall[-1] para pegar o link da última seta - a direita.
            prox_pag = response.css("li.c-pagination__arrow a::attr(href)").getall()[-1]
            splash_args = {
                'wait': 1.5,
            }
            yield SplashRequest(prox_pag, self.parse_coments, args=splash_args)

        # from scrapy.shell import inspect_response
        # inspect_response(response, self)
