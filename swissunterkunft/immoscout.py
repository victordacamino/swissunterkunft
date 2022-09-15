# packages
from gc import callbacks
import time
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
import urllib
import json

# scraper class


class Immoscout(scrapy.Spider):
    # scraper/spider name
    name = 'immoscout'

    # base URL
    base_url = 'https://www.immoscout24.ch/en/real-estate/rent/city-'

    # custom header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
    }

    # string query parameters
    params = {
        'pn': ''
    }

    # current page crawled
    current_page = 1

    # custom settings
    custom_settings = {
        'FEED_FORMAT': 'csv',
        'FEED_URI': 'immoscout.csv'
    }

    # crawler's entry
    def start_requests(self):
        # city names
        cities = ''

        # open "swiss_cities.txt" file
        with open('swiss_cities.txt', 'r') as f:
            for line in f.read():
                cities += line

        # init cities
        cities = cities.split('\n')

        # init count for cities
        count = 1

        # loop over in cities
        for city in cities:
            # reset current page
            self.current_page = 1

            # init string query parameters
            self.params['pn'] = self.current_page

            # generate city URL to crawl
            url = self.base_url + city + '?' + \
                urllib.parse.urlencode(self.params)

            # crawl given city
            yield scrapy.Request(url=url, headers=self.headers, meta={'city': count, 'totalNbCities': len(cities)}, callback=self.parse, errback=self.parse)

            # increment cities count
            count += 1

    # parse content
    def parse(self, res):
        # extract data from meta container
        count = res.meta.get('city')
        totalNbCities = res.meta.get('totalNbCities')

        # loop over property cards
        for card in res.css('div[class="Body-jQnOud bjiWLb"]'):
            # most of the time, the "details input string" = X rooms, Y m2, CHF Z (but not always, so we need to treat the special cases)
            # get the base input string
            detailsString = ''.join(card.css(
                'h3[class="Box-cYFBPY edGgnU Heading-daBLVV dOtgYu"] *::text').getall())

            # check if price is in the string
            if detailsString.find(".\u2014") != -1:
                priceParsed = detailsString.split(
                    "CHF ", 1)[1].split(".\u2014", 1)[0]
            else:
                priceParsed = '-1'

            # check if number of rooms is in the string
            if detailsString.find(" room") != -1:
                nbRoomsParsed = detailsString.split(" room", 1)[0]
            else:
                nbRoomsParsed = '-1'

            # check if surface is in the string
            if detailsString.find(" m\u00b2") != -1:
                if detailsString.find(" room") != -1:
                    surfaceParsed = detailsString.split(
                        " m\u00b2", 1)[0].split(", ", 1)[1]
                else:
                    surfaceParsed = detailsString.split(" m\u00b2", 1)[0]
            else:
                surfaceParsed = '-1'

            # property features
            features = {
                'title': card.css('h2[class="Box-cYFBPY cmzxWH Title__TitleStyled-JDiVe zBlIG"]::text').getall()[1],
                'price': priceParsed,
                'nbRooms': nbRoomsParsed,
                'surface': surfaceParsed,
                'address': card.css('span[class="AddressLine__TextStyled-eaUAMD iBNjyG"]::text').getall()[0]
            }

            # store output to CSV
            yield features

        # crawl next pages if available
        try:
            # extract number of total pages
            if len([int(page) for page in res.css('div[class="Box-cYFBPY Flex-feqWzG dpEUFz dCDRxm"] *::text').getall() if page.isdigit()]) > 1:
                # increment current page by 1
                self.current_page += 1
                total_pages = max([int(page) for page in res.css(
                    'div[class="Box-cYFBPY Flex-feqWzG dpEUFz dCDRxm"] *::text').getall() if page.isdigit()])
            else:
                total_pages = 1
                self.current_page = 9999

            # increment page number string query parameter
            self.params['pn'] = self.current_page

            # create next page URL to crawl
            next_page = res.url.split(
                '?')[0] + '?' + urllib.parse.urlencode(self.params)

            # print debugging info
            self.log('Crawling city %s out of %s cities' %
                     (count, totalNbCities))
            self.log('Crawling page %s out of %s pages' %
                     (self.current_page, total_pages))

            # crawl next page URL if available
            if self.current_page <= total_pages:
                # crawl next page recursively
                yield scrapy.Request(url=next_page, headers=self.headers, meta={'city': count, 'totalNbCities': totalNbCities}, callback=self.parse, errback=self.parse)

        except Exception as e:
            print(e)


# main driver
if __name__ == '__main__':
    # run scraper
    process = CrawlerProcess()
    process.crawl(Immoscout)
    process.start()
