#!/usr/bin/python3
# -*- coding: utf-8 -*
__author__ = "gisly"

import sys
from enum import Enum
import time
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime



NEWSPAPER_MAIN_URL = 'http://www.khanty-yasang.ru'
NEWSPAPER_URL = NEWSPAPER_MAIN_URL + '/luima-seripos/rubrics/%s?page=%s'
RESOURCES_FOLDER = '../resources/'
DATETIME_FORMAT_SITE = '%m/%d/%Y - %H:%M'
DATETIME_FORMAT_FILENAME = '%Y_%m_%d_%H_%m'

TOPIC_IDENTIFIERS = {'news' : 14,
                     'politics' : 21,
                     'life' : 17,
                     'culture' : 15,
                     'finno-ugric': 18,
                     'literature': 19,
                     'children' : 22}
NUM_ARTICLES = 0
PAUSE_SEC = 10

CHARS_REPLACE = {'\uf50e': 'А̄',
                 '\uf50f': 'а̄',
                 '\uf510': 'Е̄',
                 '\uf511': 'е̄',
                 '\uf512': 'Ё̄',
                 '\uf513': 'ё̄',
                 '\uf518': 'О̄',
                 '\uf519': 'о̄',
                 '\uf520': 'Ы̄',
                 '\uf521': 'ы̄',
                 '\uf522': 'Э̄',
                 '\uf523': 'э̄',
                 '\uf52c': 'Ю̄',
                 '\uf52d': 'ю̄',
                 '\uf528': 'Я̄',
                 '\uf529': 'я̄',
                 }

def scrape_luima_seripos(page_from, page_to, topic):
    if page_from == 0:
        page_from = 1
    current_page = page_from
    while current_page <= page_to:
        scrape_luima_seripos_page(current_page, topic)
        current_page += 1

def scrape_luima_seripos_page(current_page, topic):
    if topic == Topic.ALL:
        for topic in iter(Topic):
            if topic.topic_identifier != -1:
                scrape_luima_seripos_page_by_topic(current_page, topic)
    else:
        scrape_luima_seripos_page_by_topic(current_page, topic)

def scrape_luima_seripos_page_by_topic(current_page, topic):
    text_links = get_links_to_full_text(current_page, topic.topic_identifier)
    for index, text_link in enumerate(text_links):
        scrape_luima_seripos_article(text_link, topic)
        if (index > 0) and (index % 10 == 0):
            print('parsed %s pages' % index)
            time.sleep(PAUSE_SEC)
    print('page #%s (topic=%s) parsed' % (current_page, topic.name))
    time.sleep(PAUSE_SEC)


def scrape_luima_seripos_article(text_link, topic):
    article = parse_luima_seripos_article(text_link)
    if article is None:
        return
    text_date_formatted = article['text_date'].strftime(DATETIME_FORMAT_FILENAME)
    filename_prefix = text_date_formatted + '_' + topic.name + '_' + article['global_id']
    write_text_to_file(filename_prefix, article, 'mns')
    write_text_to_file(filename_prefix, article, 'rus')

def write_text_to_file(filename_prefix, article, language_code):
    filename = os.path.join(RESOURCES_FOLDER, filename_prefix + '_' + language_code  +'.txt')
    with open(filename, 'w', encoding='utf-8', newline='') as fout:
        fout.write(article['link'] + '\r\n')
        fout.write(article['title_' + language_code] + '\r\n')
        fout.write(article['text_' + language_code] + '\r\n')

def parse_luima_seripos_article(text_link):
    try:
        url = create_text_url(text_link)
        response_text = get_text_from_url(url)
        response_parsed = BeautifulSoup(response_text, 'html.parser')
        titles = parse_titles(response_parsed)
        if not(titles):
            return None
        texts = parse_texts(response_parsed)
        mansi_title = normalize_characters(titles[0])
        if len(titles) < 2:
            russian_title = '*'
        else:
            russian_title = titles[1]
        mansi_text = normalize_characters(texts[0])
        russian_text = texts[1]
        text_date = parse_date(response_parsed)
        text_link_parts = text_link.split('/')
        number_parts = text_link_parts[2].split('no')[1].strip('-').split('-')
        if len(number_parts) > 1:
            newspaper_number = number_parts[0]
            newspaper_global_number = number_parts[1]
        else:
            newspaper_number = number_parts[0:2]
            newspaper_global_number = number_parts[2:]
        global_id = text_link_parts[3]
        return {'link' : url,
                'title_mns': mansi_title,
                'text_mns': mansi_text,
                'title_rus': russian_title,
                'text_rus': russian_text,
                'newspaper_number' : newspaper_number,
                'newspaper_global_number' : newspaper_global_number,
                'global_id' : global_id,
                'text_date' : text_date
                }
    except Exception as e:
        print('Error occurred when parsing %s:%s' % (text_link, str(e)))

def normalize_characters(mansi_text):
    for key, value in CHARS_REPLACE.items():
        mansi_text = mansi_text.replace(key, value)
    return mansi_text

def parse_titles(response_parsed):
    titles = response_parsed.find_all('div', class_='field-title')
    return [title.text.strip() for title in titles]

def parse_texts(response_parsed):
    test_list = []
    texts = response_parsed.find_all('div', class_='field-item even')
    for text in texts:
        text_paragraphs = list(text.stripped_strings)
        text_with_whitespace_removed = '\r\n'.join(text_paragraphs).strip()
        test_list.append(text_with_whitespace_removed)
    return test_list

def parse_date(response_parsed):
    return transform_site_tag_to_date(response_parsed.find('div', class_='data').text)

def transform_site_tag_to_date(site_tag):
    sit_tag_date_time = site_tag.split(',')[1].strip()
    return datetime.strptime(sit_tag_date_time, DATETIME_FORMAT_SITE)

def get_links_to_full_text(current_page, topic_identifier):
    url = create_page_url(current_page, topic_identifier)
    response_text = get_text_from_url(url)
    response_parsed = BeautifulSoup(response_text, 'html.parser')
    text_links = response_parsed.find_all('a', rel='tag')
    return [text_link.attrs['href'] for text_link in text_links]

def get_text_from_url(url):
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        raise Exception('Error for page=%s: returns status=%s)'
                        % (url, response.status_code)
                        )
    return response.text

def create_page_url(current_page, topic_identifier):
    page_num_in_url = current_page - 1
    return NEWSPAPER_URL % (topic_identifier, page_num_in_url)

def create_text_url(text_link):
    return NEWSPAPER_MAIN_URL + text_link

class Topic(Enum):
    NEWS = (14)
    POLITICS = (21)
    LIFE = (17)
    CULTURE = (15)
    FU = (18)
    LITERATURE = (19)
    CHILDREN = (22)
    ALL = (-1)

    def __init__(self, topic_identifier):
        self.topic_identifier = topic_identifier

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('usage: python luima_seripos_scraper.py <from> <to> <topic:optional>')
    page_from = int(sys.argv[1])
    page_to = int(sys.argv[2])
    if len(sys.argv) > 4:
        topic = Topic[sys.argv[3]]
    else:
        topic = Topic.ALL
    scrape_luima_seripos(page_from, page_to, topic)