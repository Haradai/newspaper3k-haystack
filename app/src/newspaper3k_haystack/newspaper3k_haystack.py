from haystack.nodes.base import BaseComponent
from haystack.schema import Document
from newspaper import Article
from newspaper import Config
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import os
class newspaper3k_scraper(BaseComponent):
    '''
    A simple newspaper3k haystack node wrapper.
    '''
    # If it's not a decision component, there is only one outgoing edge
    outgoing_edges = 1

    def __init__(self,
    headers: dict = None,
    request_timeout: int = None
    ):
        """
        :param header: HTTP headers information.
            e.g.
            {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}
        
        :param request_timeout: 
        """
        self.config = Config()
        if headers != None:
            self.config.headers = headers 
        if request_timeout != None:
            self.config.request_timeout = request_timeout


    def run(self, 
    query: str, 
    lang: str = None, 
    metadata: bool = False,
    links: bool = False,
    keywords: bool = False,
    summary: bool = False,
    path: str = None,
    load: bool = False,
    verbose_fails: bool = True
    ):
        '''
        :param query: String containing the webpage to scrape.
        :param lang: (None by default) language to process the article with, if None autodetected.
            Available languages are: (more info at https://newspaper.readthedocs.io/en/latest/)
            input code      full name

            ar              Arabic
            ru              Russian
            nl              Dutch
            de              German
            en              English
            es              Spanish
            fr              French
            he              Hebrew
            it              Italian
            ko              Korean
            no              Norwegian
            fa              Persian
            pl              Polish
            pt              Portuguese
            sv              Swedish
            hu              Hungarian
            fi              Finnish
            da              Danish
            zh              Chinese
            id              Indonesian
            vi              Vietnamese
            sw              Swahili
            tr              Turkish
            el              Greek
            uk              Ukrainian
            bg              Bulgarian
            hr              Croatian
            ro              Romanian
            sl              Slovenian
            sr              Serbian
            et              Estonian
            ja              Japanese
            be              Belarusian

        :param metadata: (False by default) Wether to get article metadata.
        :param links: (False by default) Wether to get links contained in the article.
        :param keywords: (False by default) Wether to save the detected article keywords as document metadata.
        :param summary: (False by default) Wether to summarize the document (through nespaper3k) and save it as document metadata.
        :param path: (None by default) Path where to store the downloaded article html, if None, not downloaded. Ignored if load=True
        :param load: (False by default) If true query should be a local path to an html file to scrape or a folder containing html files.
        :param verbose_fails (True by default) If true print fail of downloads and text extractions.
        '''
        if load:
            #check if path was passed 
            if os.path.isdir(query):
                files = os.listdir("articles")
                htmls_pths = [f for f in files if (f.split(".")[-1]=="html")] #filter only html files

                docs = []
                pbar = tqdm(total=len(htmls_pths),desc="Scraping: " + query) #tqdm bar
                for pth in htmls_pths:
                    #call itself but for each file
                    docs += self.run(query+"/"+pth,lang,metadata,links,keywords,summary,load=load,verbose_fails=verbose_fails)[0]["documents"]
                    pbar.desc = "Scraping: " + query+"/"+pth[:20]+"..."
                    pbar.update(1)

                return {"documents":docs} , "output_1"
            
            else: #should be a simple html file or an error will be raised by nespaper3k
                with open(query, 'rb') as file:
                    html = file.read()
                article = Article(url = query)
                
                try:
                    article.set_html(html)
                    article.parse()
                except:
                    if verbose_fails:
                        print(f"Unable to load the file {query}")
                    return {"documents":[]} , "output_1"

        else: #downloading from internet
            if lang is None:
                article = Article(query,config=self.config)
            else:
                article = Article(query,language=lang,config=self.config)
            
            #try to downnload, in case of failure return empty list
            try:
                article.download()
                article.parse()
            except:
                if verbose_fails:
                    print(f"Unable to download the article {query}")
                return {"documents":[]} , "output_1"
            
            #if wanted locally save as html file
            if path is not None:
                assert os.path.isdir(path), f"The provided path {path} doesn't exist"
                with open(path + "/" + query.replace("/","_")+ ".html", "w") as file:
                    # Write to the file
                    file.write(article.html)


        # before continuing processing check if article parse wasn't able to get any text
        if len(article.text) == 0 :
            if verbose_fails:
                print(f"Unable to extract text from {query}")
            return {"documents":[]} , "output_1"
        
        #process docs
        document_dict = {
            "content":article.text,
            "content_type": "text",
            "meta": {
                "url":query,
                "source_url": article.source_url,
                "lang":article.meta_lang
                }
            }
        
        if metadata:
            document_dict["meta"]["title"] = article.title
            document_dict["meta"]["authors"] = article.authors
            document_dict["meta"]["publish_date"] = article.publish_date
            document_dict["meta"]["movies_url"] = article.movies
            document_dict["meta"]["top_image_url"] = article.top_image

        if links:
            soup = BeautifulSoup(article.html, features="lxml") #using lxml parser
            links = list(set([link.get("href") for link in soup.findAll("a")]))
            #some retrieved hrefs are just a subdirectory in the main page, reconstruct those.
            clean_links = []
            for l in links:
                if l is not None:
                    if("http" not in l) and ("www" not in l):
                        clean_links.append(article.source_url + l)
                    else:
                        clean_links.append(l)

            document_dict["meta"]["links"] = clean_links

        if keywords or summary: #this conditional is for efficiency, no need to run nlp function if we don't want the data
            article.nlp()
        
        if keywords:
            document_dict["meta"]["article_keywords"] = article.keywords

        if summary:
            document_dict["meta"]["summary"] = article.summary

        document = Document.from_dict(document_dict)
        
        output={
            "documents": [document],
        }
        return output, "output_1"

    def run_batch(self, 
    queries: list, 
    lang: str = None, 
    metadata: bool = False,
    links: bool = False,
    keywords: bool = False,
    summary: bool = False,
    path: str = None,
    load: bool = False,
    verbose_fails: bool = True
    ):
        '''
        :param query: list of strings containing the webpages to scrape.
        :param lang: (None by default) language to process the article with, if None autodetected.
            Available languages are: (more info at https://newspaper.readthedocs.io/en/latest/)
            input code      full name

            ar              Arabic
            ru              Russian
            nl              Dutch
            de              German
            en              English
            es              Spanish
            fr              French
            he              Hebrew
            it              Italian
            ko              Korean
            no              Norwegian
            fa              Persian
            pl              Polish
            pt              Portuguese
            sv              Swedish
            hu              Hungarian
            fi              Finnish
            da              Danish
            zh              Chinese
            id              Indonesian
            vi              Vietnamese
            sw              Swahili
            tr              Turkish
            el              Greek
            uk              Ukrainian
            bg              Bulgarian
            hr              Croatian
            ro              Romanian
            sl              Slovenian
            sr              Serbian
            et              Estonian
            ja              Japanese
            be              Belarusian

        :param metadata: (False by default) Wether to get article metadata.
        :param links: (False by default) Wether to get links contained in the article.
        :param keywords: (False by default) Wether to save the detected article keywords as document metadata.
        :param summary: (False by default) Wether to summarize the document (through nespaper3k) and save it as document metadata.
        :param path: (None by default) Path where to store the downloaded articles html, if None, not downloaded. Ignored if load=True
        :param load: (False by default) If true query should be a local path to an html file to scrape.
        :param verbose_fails (True by default) If true print fail of downloads and text extractions.
        '''
        docs = []
        for web in tqdm(queries):
            docs += self.run(web,lang,metadata,links,keywords,summary,path,load,verbose_fails)[0]["documents"]

        output={
            "documents": docs,
        }
        return output, "output_1"

class newspaper3k_crawler(BaseComponent):
    """
    A simple web crawler using newspaper3k scraper node.
    """
    outgoing_edges = 1 

    def __init__(self,
    headers: dict = None,
    request_timeout: int = None
    ):
        """
        :param header: HTTP headers information.(Optional, if none is passed nespaper3k default is used)
            e.g.
            {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:78.0) Gecko/20100101 Firefox/78.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}
        
        :param request_timeout: request timeout in seconds?* (Optional, if none is passed nespaper3k default is used)
        """
        self.crawled_urls =[] 
        self.stack = []
        self.scraper_node = newspaper3k_scraper(headers,request_timeout)


    def run(self,
    query: str,
    n_articles: int,
    beam: int = 0,
    filters: list = None,
    keep_links: bool = False,
    lang: str = None, 
    metadata: bool = False,
    links: bool = False,
    keywords: bool = False,
    summary: bool = False,
    path: str = None,
    verbose_fails: bool = False
    ):
        """
        :param query: initial url to start scraping
        :param n_articles: number of articles to scrape
        :param beam: number of articles from each scraped website to prioritize in the crawl queue.
            If 0 then priority of scrape will be a simple continuous pile of found links after each scrape. (BFS). 
            If 1 then would be performing (DFS).
        :param filters: dictionary with lists of strings that the urls should contain or not. Keys: positive and negative.
            Urls will be checked to contain at least one positive filter and none of the negatives.
            e.g.
            {positive: [".com",".es"],
            negative: ["facebook","instagram"]}
        :param keep_links: (False by default) Wether to keep the found links in each page as document metadata or not
        :param lang: (None by default) language to process the article with, if None autodetected.
            Available languages are: (more info at https://newspaper.readthedocs.io/en/latest/)
            input code      full name
            ar              Arabic
            ru              Russian
            nl              Dutch
            de              German
            en              English
            es              Spanish
            fr              French
            he              Hebrew
            it              Italian
            ko              Korean
            no              Norwegian
            fa              Persian
            pl              Polish
            pt              Portuguese
            sv              Swedish
            hu              Hungarian
            fi              Finnish
            da              Danish
            zh              Chinese
            id              Indonesian
            vi              Vietnamese
            sw              Swahili
            tr              Turkish
            el              Greek
            uk              Ukrainian
            bg              Bulgarian
            hr              Croatian
            ro              Romanian
            sl              Slovenian
            sr              Serbian
            et              Estonian
            ja              Japanese
            be              Belarusian
        :param metadata: (False by default) Wether to get article metadata.
        :param keywords: (False by default) Wether to save the detected article keywords as document metadata.
        :param summary: (False by default) Wether to summarize the document (through nespaper3k) and save it as document metadata.
        :param path: (None by default) Path where to store the downloaded articles html, if None, not downloaded.
        :param verbose_fails (False by default) If true print fail of downloads and text extractions.
        """
        crawl_count = 0
        current_seed = query
        documents = []

        pbar = tqdm(total=n_articles,desc="Crawling " + current_seed[:80]) #tqdm bar
        while crawl_count < n_articles:
            #scrape current seed
            docs = self.scraper_node.run(query=current_seed,links=True,lang=lang,metadata=metadata,keywords=keywords,summary=summary,path=path,verbose_fails=verbose_fails)[0]["documents"]

            if len(docs) == 0: #unable to scrape
                if verbose_fails:
                    print("skipping to next url")
                crawl_count -= 1 #to compensate not scraping this web

            else:
                doc = docs[0] #get article

                #get links and filter them
                links = doc.meta["links"]
                links = self._filter_urls(links,filters=filters)

                #add found urls to pile
                beam_slice_idx = len(self.crawled_urls)*crawl_count - len(self.crawled_urls)
                self.stack = self.stack[:beam_slice_idx] + links[:beam] +  self.stack[beam_slice_idx:] + links[beam:]

                #save document
                if not keep_links:
                    del doc.meta["links"]

                documents.append(doc)

                #go to next webpage to crawl
                self.crawled_urls.append(current_seed)

            #check if there are links left to crawl
            if len(self.stack) == 0:
                print(f"Unable to fulfill number of articles to scrape, didn't find enough links. Number of articles scraped: {crawl_count}")
                break


            self.crawled_urls.append(current_seed) #saved scraped article, even if it didn't end up in documents because unable to download or extract text
            current_seed = self.stack[0]
            self.stack = self.stack[1:]
            crawl_count += 1
            pbar.desc = "Crawling " + current_seed[:80] #crop url
            pbar.update(1)

        output={
            "documents": documents
        }
        return output, "output_1"

    def run_batch(self,
    query: list,
    n_articles: int,
    beam: int = 0,
    filters: list = None,
    keep_links: bool = False,
    lang: str = None, 
    metadata: bool = False,
    links: bool = False,
    keywords: bool = False,
    summary: bool = False,
    path: str = None,
    verbose_fails: bool = False
    ):
        """
        :param query: list of initial urls to start scraping
        :param n_articles: number of articles to scrape per initial url
        :param beam: number of articles from each scraped website to prioritize in the crawl queue.
            If 0 then priority of scrape will be a simple continuous pile of found links after each scrape. (BFS). 
            If 1 then would be performing (DFS).
        :param filters: dictionary with lists of strings that the urls should contain or not. Keys: positive and negative.
            Urls will be checked to contain at least one positive filter and none of the negatives.
            e.g.
            {positive: [".com",".es"],
            negative: ["facebook","instagram"]}
        :param keep_links: (False by default) Wether to keep the found links in each page as document metadata or not
        :param lang: (None by default) language to process the article with, if None autodetected.
            Available languages are: (more info at https://newspaper.readthedocs.io/en/latest/)
            input code      full name
            ar              Arabic
            ru              Russian
            nl              Dutch
            de              German
            en              English
            es              Spanish
            fr              French
            he              Hebrew
            it              Italian
            ko              Korean
            no              Norwegian
            fa              Persian
            pl              Polish
            pt              Portuguese
            sv              Swedish
            hu              Hungarian
            fi              Finnish
            da              Danish
            zh              Chinese
            id              Indonesian
            vi              Vietnamese
            sw              Swahili
            tr              Turkish
            el              Greek
            uk              Ukrainian
            bg              Bulgarian
            hr              Croatian
            ro              Romanian
            sl              Slovenian
            sr              Serbian
            et              Estonian
            ja              Japanese
            be              Belarusian
        :param metadata: (False by default) Wether to get article metadata.
        :param keywords: (False by default) Wether to save the detected article keywords as document metadata.
        :param summary: (False by default) Wether to summarize the document (through nespaper3k) and save it as document metadata.
        :param path: (None by default) Path where to store the downloaded articles html, if None, not downloaded.
        :param verbose_fails (False by default) If true print fail of downloads and text extractions.
        """

        docs = []
        for web in query:
            docs += self.run(
                    web,
                    n_articles = n_articles,
                    beam = beam,
                    filters = filters,
                    keep_links = keep_links,
                    lang = lang, 
                    metadata = metadata,
                    links = links,
                    keywords = keywords,
                    summary = summary,
                    path=path,
                    verbose_fails=verbose_fails
                    )[0]["documents"]

        output={
            "documents": docs,
        }
        return output, "output_1"

    def _filter_urls(self,urls,filters):
        #no filters
        if filters is None:
            return urls

        #filter urls
        pos = [re.compile(pattern) for pattern in filters["positive"]]
        neg = [re.compile(pattern) for pattern in filters["negative"]]
        filtered = []

        for url in urls: 
            neg_aux = False
            if url not in self.crawled_urls and url not in self.stack: #filter to not repeat urls
                #for a long list of neg variables this should be faster than using any()?
                for neg_patt in neg:
                    if neg_patt.search(url):
                        neg_aux=True
                        break
                if neg_aux:
                    continue

                for pos_patt in pos: #at least one
                    if pos_patt.search(url):
                        filtered.append(url)
                        break

        return filtered
