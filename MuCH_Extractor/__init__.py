import requests, re, os, en_core_web_sm, time, urllib.parse, pandas as pd
from lyricsgenius import Genius
import musicbrainzngs as mbz
from dotenv import load_dotenv
from qwikidata.sparql import return_sparql_query_results
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer, util
from bs4 import BeautifulSoup
from SPARQLWrapper import SPARQLWrapper, JSON
from bardapi import Bard
from nltk.corpus import wordnet as wn
from rdflib import Graph, URIRef, Literal, Namespace, RDF, RDFS, OWL, XSD, BNode

nlp = en_core_web_sm.load()
load_dotenv()





class SongDataCollector(object):

    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')
    MUSICBRAINZ_USER = os.getenv('MUSICBRAINZ_USER')
    MUSICBRAINZ_TOKEN = os.getenv('MUSICBRAINZ_TOKEN')
    MBZ_USER_AGENT = "MucH-ExSo"
    MBZ_APP_VERSION = "0.1"


    def __init__(self, spotify_id):
        self.spotify_id = spotify_id
        self.spotify_headers = self.get_spotify_headers()

    def __str__(self):
        return f"Song: {self.spotify_id}"


    #_______________________________________________________
    # Spotify API
    #_______________________________________________________

    def get_spotify_headers(self):
        # Get headers for Spotify API
        data = {
                'grant_type': 'client_credentials',
                'client_id': self.SPOTIFY_CLIENT_ID,
                'client_secret': self.SPOTIFY_CLIENT_SECRET,
                }
        
        response = requests.post('https://accounts.spotify.com/api/token', data=data).json()
        token_type = response['token_type']
        access_token = response['access_token']
        return { 'Authorization': str(token_type) + ' ' + str(access_token), }


    def get_spotify_song(self):
        # Get song data from Spotify API
        return requests.get(f'https://api.spotify.com/v1/tracks/{self.spotify_id}', headers=self.spotify_headers).json()


    def get_spotify_artist(self, artist_id):
        # Get song data from Spotify API
        return requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=self.spotify_headers).json()


    def save_spotify_data(self):
        # Save song data from Spotify API
        song = {}
        song_data = self.get_spotify_song()
        song['spotify-id'] = song_data['id']
        song['spotify-href'] = song_data['href']
        song['name'] = re.sub(r'\s?-?\s?([0-9]+)?\s?\(?[Rr]emaster(ed)?\)?','', song_data['name'])
        song['album-name'] = song_data['album']['name']
        song['artists'] = []
        for artist in song_data['artists']:
            artist_dict = {}
            artist_dict['spotify-id'] = artist['id']
            artist_dict['spotify-href'] = artist['href']
            artist_dict['name'] = artist['name']
            get_art =  self.get_spotify_artist(artist['id'])
            artist_dict['genres'] = get_art['genres']
            song['artists'].append(artist_dict)
        song['isrc'] = song_data['external_ids']['isrc']
        return song

#_______________________________________________________
# Genius API
#_______________________________________________________


    def save_genius_data(self, song_name, artist_name, store=dict()):
        genius = Genius(self.GENIUS_ACCESS_TOKEN)
        genius_song = genius.search_song(song_name, artist_name)
        genius_id = genius_song.id

        store['genius_id'] = genius_id
        store['genius_url'] = genius_song.url
        store['lyrics'] = re.sub(r'[0-9]+\sContributors.+\sLyrics\n', '', genius.lyrics(genius_id, remove_section_headers=True))
        
        annotations_list = []
        annotations = genius.song_annotations(genius_id)
        for tup in annotations:
            new_tup = (tup[0], tup[1][0][0].replace('\n\n', ' ').replace('\n', ' ').replace('  ', '')) #Here I take just the first annotation (I haven't found yet a fragment with more than one annotation)
            annotations_list.append(new_tup)
        store['annotations'] = annotations_list
        return store

#_______________________________________________________
# MusicBrainz API
#_______________________________________________________ 

    def get_musicbrainz_song(self, isrc, auth=False):
        # Get song data from MusicBrainz API
        if auth:
            mbz.set_useragent(self.MBZ_USER_AGENT, self.MBZ_APP_VERSION)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        mbz_song = mbz.get_recordings_by_isrc(isrc)
        return mbz.get_recording_by_id(mbz_song['isrc']['recording-list'][0]['id'], includes=['artists'])
    

    def get_musicbrainz_artist(self, art_id, auth=False):
        # Get artist data from MusicBrainz API
        if auth:
            mbz.set_useragent(self.MBZ_USER_AGENT, self.MBZ_APP_VERSION)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        return mbz.get_artist_by_id(art_id, includes=["url-rels", "tags"])

    
    def save_musicbrainz_data(self, isrc, store=dict()):
        # Save song data from MusicBrainz API
        mbz.set_useragent(self.MBZ_USER_AGENT, self.MBZ_APP_VERSION)
        mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)

        mbz_song = self.get_musicbrainz_song(isrc)
        store['musicbrainz_id'] = mbz_song['recording']['id']
        artist_ids = [artist['artist']['id'] for artist in mbz_song['recording']['artist-credit']]
        artist_data = {}
        for artist_id in artist_ids:
            if artist_id not in artist_data:
                artist_data[artist_id] = self.get_musicbrainz_artist(artist_id)
        store['artists'] = []
        for artist in mbz_song['recording']['artist-credit']:

            if store['name'].strip().lower() == artist['artist']['name'].strip().lower():
                if 'disambiguation' in artist['artist']:
                    store['disambiguation'] = artist['artist']['disambiguation']
                store['mbz_id'] = artist['artist']['id']
                if store['mbz_id'] in artist_data:
                    wts = artist_data[store['mbz_id']]
                    store['type'] = wts['artist']['type']
                    for url in wts['artist']['url-relation-list']:
                        if url['type'] == 'wikidata':
                            store['wikidata_url'] = url['target']
        return store


#_______________________________________________________
# Get all data
#_______________________________________________________

    def get_song_data(self):
        # Get song data from all APIs
        song_data = self.save_spotify_data()
        song_data = self.save_genius_data(song_data['name'], song_data['artists'][0]['name'], song_data)
        song_data = self.save_musicbrainz_data(song_data['isrc'], song_data)
        return song_data


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________




class InformationExtractor(object):
    def __init__(self, annotation_list, song_data):
        self.annotation_list = annotation_list
        self.song_data = song_data
    
    def get_entities(self):
        creative_works = {}
        people = {}
        for annotation in self.annotation_list:
            doc = nlp(annotation[1])
            for ent in doc.ents:
                ent_text = ent.text
                ent_sub_str = re.sub(r'[’\']s$', '', ent_text)
                ent_sub_str = re.sub(r'[^A-Za-z0-9]$', '', ent_sub_str)
                if ent.label_ == 'WORK_OF_ART':
                    if ent_sub_str not in {self.song_data['album-name'], self.song_data['name']}:
                        if ent_sub_str not in creative_works:
                            creative_works[ent_sub_str] = {'count': 0, 'annotation_number': {}}
                if ent.label_ == 'PERSON':
                    if ent_sub_str not in {artist['name'] for artist in self.song_data['artists']}:
                        if ent_sub_str not in people:
                            people[ent_sub_str] = {'count': 0, 'annotation_number': {}}
        return creative_works, people
    

    def store_entities(self, creative_works, people):
        for ann_num, ann in enumerate(self.annotation_list):
            clean_txt = re.sub(r'[^A-Za-z0-9\'\’]', ' ', ann[1]) #remove all the non alphanumeric characters
            words = clean_txt.split(' ') #split the string into a list of words

            for cw in creative_works: #for every work of art in the dictionary
                if len(cw.split(' ')) == 1: #if the work of art is one word
                    ann_occurrences = words.count(cw) #count the number of occurrences of the word in the annotation
                    if ann_occurrences > 0: #if the word is in the annotation
                        creative_works[cw]['annotation_number'][ann_num] = ann_occurrences #add the number of occurrences to the dictionary
                        creative_works[cw]['count'] += ann_occurrences #add the number of occurrences to the total count
                else: #if the work of art is more than one word
                    ann_occurrences = clean_txt.count(cw) #here changes the variable on which to count
                    if ann_occurrences > 0: #if the word is in the annotation
                            creative_works[cw]['annotation_number'][ann_num] = ann_occurrences #add the number of occurrences to the dictionary
                            creative_works[cw]['count'] += 1 #add the number of occurrences to the total count
                
            for per in people: #for every person in the dictionary
                if len(per.split(' ')) == 1: #if the person is one word
                    ann_occurrences = words.count(per) #count the number of occurrences of the word in the annotation
                    if ann_occurrences > 0: #if the word is in the annotation
                        people[per]['annotation_number'][ann_num] = ann_occurrences #add the number of occurrences to the dictionary
                        people[per]['count'] += ann_occurrences #add the number of occurrences to the total count
                else: #if the person is more than one word
                    ann_occurrences = clean_txt.count(per) #here changes the variable on which to count
                    if ann_occurrences > 0: #if the word is in the annotation
                        people[per]['annotation_number'][ann_num] = ann_occurrences #add the number of occurrences to the dictionary
                        people[per]['count'] += 1 #add the number of occurrences to the total count
                    
                    remove_occurrences = clean_txt.replace(per, ' ').split(' ') #remove the occurrences of the person from the annotation
                    ps = per.split(' ')[-1] #get the last word of the person which is more likely to be the surname
                    new_ann_occurrences = remove_occurrences.count(ps) #count the number of occurrences of the last word of the person in the annotation
                    if new_ann_occurrences > 0: #if the word is in the annotation
                        if ann_num in people[per]['annotation_number']: #if the annotation number is already in the dictionary
                            people[per]['annotation_number'][ann_num] += new_ann_occurrences #add the number of occurrences to the dictionary
                        else: #if the annotation number is not in the dictionary
                            people[per]['annotation_number'][ann_num] = new_ann_occurrences #add the number of occurrences to the dictionary
                        people[per]['count'] += new_ann_occurrences #add the number of occurrences to the total count

        return creative_works, people
    

    def extract_information(self):
        creative_works, people = self.get_entities()
        creative_works, people = self.store_entities(creative_works, people)
        return creative_works, people
    

#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________



class CandidateExtractor(object):
    def __init__(self, creative_works):
        self.creative_works = creative_works
    
    def wikidata_reconciliation(self, query):
        API_WD = "https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': 'en',
            'type': 'item',
            'search': query # the query string
        }
        return requests.get(API_WD, params = params).json()
    


    def get_candidates(self):
        candidates = {}
        for cw in self.creative_works:
            candidates[cw] = []
            r = self.wikidata_reconciliation(cw)

            if 'search' in r and len(r['search']) >= 1: # if there is at least one result
                for result in r['search']:
                    qid = result['title']
                    query_string = """ASK { wd:"""+qid+""" wdt:P31 ?type. ?type wdt:P279* wd:Q17537576 }""" # query string to check if the entity is ANYTHING BEING SUBCLASS OF CREATIVE WORK
                
                    # this time I query the wikidata endpoint directly
                    res = return_sparql_query_results(query_string) 
                    
                    if res["boolean"] == True: #If the answer is true
                        entity = {}
                        #entity['class'] = 'creative work'
                        entity['id'] = result['title']
                        if 'description' in result:
                            entity['description'] = result['description']
                        else:
                            continue
                        candidates[cw].append(entity)
            if candidates[cw] == []:
                del candidates[cw]
        
        return candidates


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________



class Disambiguator(object):
    def __init__(self, people, candidates, annotations):
        self.people = people
        self.candidates = candidates
        self.annotations = annotations

    def assign_scores(self):
        req = 0 # this is the number of requests made to the WD endpoint
        people_list = []
        for per in self.people:
            people_list.append((per, self.people[per]['count']))

        for cw in self.candidates:
            relevance = len(self.candidates[cw])

            for idx, cand in enumerate(self.candidates[cw]):
                cand['relevance'] = relevance 
                relevance -= 1 #decrease for the next iteration
                cand['dependency_score'] = 0  #this is the score that will be used to compute the dependency between candidates
                cand['person_in_description'] = 0 #this is the number of times the person is mentioned in the description of the candidate
                cand['person_in_wikidata'] = 0 #this is the number of times a person is mentioned in the wikidata page of the candidate
                
                for per in people_list:
                    per_split = per[0].split(' ')
                    if len(per_split) > 1:
                        per_ts = per_split[-1]  #take the last token of the person name
                    else:
                        per_ts = per[0]

                    if per_ts in cand['description']:
                            cand['person_in_description'] += 1 #if the person is mentioned in the description of the candidate, increase the score

                    query_people = """ASK { wd:"""+cand['id']+""" ?p ?o.    
                                        ?o rdfs:label ?label.
                                        FILTER (CONTAINS((?label), '"""+per_ts+"""'))
                                        }"""
                    if req % 5 == 0:
                        time.sleep(5) # to avoid to be blocked by WD endpoint for too many requests in a short time 
                    res_people = return_sparql_query_results(query_people)
                    req += 1

                    if res_people["boolean"] == True:
                        cand['person_in_wikidata'] += 1

                #____________Second query____________
                qs = "VALUES ?items { "      # this is the SPARQL query string to complete
                for i in self.candidates[cw]:    # i repeat the loop since for every candidate i want to ask if it is dependent on at least one of the other candidates (meaning it's a derivative wor of another candidate)
                    if self.candidates[cw].index(i) == idx:
                        continue
                    else:
                        wd_id = "wd:"+i['id']
                        qs += wd_id+" "
                qs += "}"

                query_dependency =  """ASK {
                                            VALUES ?d { wdt:P144 wdt:P737 wdt:P941 wdt:P8371 }
                                            """+qs+"""
                                            {
                                                wd:"""+cand['id']+""" ?d ?items.
                                            }UNION{
                                                ?items wdt:P4969 wd:"""+cand['id']+""".
                                            }
                                    }"""
                if req % 5 == 0:
                    time.sleep(5) # to avoid to be blocked by WD endpoint for too many requests in a short time
                res_dependency = return_sparql_query_results(query_dependency)
                req += 1
                if res_dependency["boolean"] == True:
                    self.candidates[cw][idx]['dependency_score'] -= 1 # if the answer is true, it means that the candidate is dependent on at least one of the other candidates, so I decrease its dependency score
        return self.candidates



    def get_clean_annotations(self):
        sents = []
        for ann in self.annotations:
            clean_txt = ann[1].replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' ')
            sts = sent_tokenize(clean_txt)
            for s in sts:
                sents.append(s)
        return sents
    

    def get_sentence_similarity(self):
        to_embed = {}
        sents = self.get_clean_annotations()
        model = SentenceTransformer('all-mpnet-base-v2') 
        for cw in self.candidates:
            to_embed[cw] = []
            for s in sents:
                if cw in s:
                    # ----- You can insert here code for defining a context window around the entity -----
                    to_embed[cw].append(model.encode(s, convert_to_tensor=True))
                    
            for ent in self.candidates[cw]:
            #________Sentence embedding________ 
                ent['description_embedding'] = model.encode(re.sub(cw, ' ', ent['description']), convert_to_tensor=True) # I remove the entity name from the description to avoid that the model learns to recognize the entity from the description itself
                #________Averaging cosine similarities________
                to_avg = [] # this is the list of cosine similarities between the entity description and the sentences containing the entity name
                for emb in to_embed[cw]:
                    cos_sim = util.cos_sim(ent['description_embedding'], emb)
                    to_avg.append(cos_sim[0][0])
                ent['similarity_score'] = round(float(sum(to_avg)/len(to_avg)), 4)
                del ent['description_embedding']
                #________Final score________
                ent['final_score'] = round(float(ent['dependency_score'] + ent['person_in_description'] + ent['person_in_wikidata'] + ent['similarity_score']), 4)
        return self.candidates
    

    def get_final_candidates(self):
        chosen = {}
        for cw in self.candidates:
            chosen[cw] = max(self.candidates[cw], key=lambda x:x['final_score'])
            if chosen[cw]['final_score'] <= 1 or chosen[cw]['similarity_score'] <= 0.2:
                del chosen[cw]
        return chosen
    

    def disambiguate(self):
        self.candidates = self.assign_scores()
        #print("\nSCORES:", self.candidates)
        self.candidates = self.get_sentence_similarity()
        #print("\nSIMILARITY:", self.candidates)
        self.candidates = self.get_final_candidates()
        #print("\nFINAL:", self.candidates)
        return self.candidates


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________


class Scraper(object):
    def __init__(self, entities):
        self.entities = entities


    def get_wikipedia_url(self):
        for cw in self.entities:
            query_string = """SELECT ?URL
                        WHERE {
                            ?URL schema:about wd:"""+self.entities[cw]['id']+""".
                            ?URL schema:isPartOf <https://en.wikipedia.org/>.
                    }"""

            res = return_sparql_query_results(query_string)
            value = res['results']['bindings'][0]['URL']['value']
            if value:
                self.entities[cw]['wikipedia_url'] = value
        return self.entities
        
        
    

    def scrape_wikipedia_page(self):
        for cw in self.entities:
            url = self.entities[cw]['wikipedia_url']
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser").select('body')[0]
            spans = soup.find_all('span', string=[re.compile('^(Cultural\s)?[Ii]mpact$'), re.compile('^[Aa]daptations?')])
            h2_tags = [span.parent for span in spans if span.parent.name == 'h2']
            li_tags = []
            for h2 in h2_tags:
                for el in h2.next_siblings:
                    if el.name == 'h2':
                        break
                    if el.name == 'ul':
                        li_tags.extend(el.find_all('li'))
            self.entities[cw]['li_tags'] = li_tags
        return self.entities
    

    def get_musical_entity_type(self, query_url):
        db_query_ent_type = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX wikipedia-en: <http://en.wikipedia.org/wiki/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?type
            WHERE { 
                    VALUES ?type { dbo:Album dbo:Song dbo:Single}
                    ?entity foaf:isPrimaryTopicOf wikipedia-en:"""+query_url+""";
                            rdf:type ?type.
                    }
            """
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setReturnFormat(JSON)
        sparql.setQuery(db_query_ent_type)
        db_type = sparql.query().convert()['results']['bindings'][0]['type']['value'].replace('http://dbpedia.org/ontology/', '')
        return db_type
   



    def get_wiki_links(self):
        for cw in self.entities:
            url = self.entities[cw]['wikipedia_url']
            entity_url = url.replace('https://en.wikipedia.org/wiki/', '')
            query_url = entity_url.replace('(', '\(').replace(')', '\)')
            db_query = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX wikipedia-en: <http://en.wikipedia.org/wiki/>
            PREFIX schema: <http://schema.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX xml: <http://www.w3.org/XML/1998/namespace>
            SELECT DISTINCT ?wikiLinks ?type ?dbEntities ?label ?mainEntityType
            WHERE { 
                    VALUES ?mainEntityType { dbo:Artist dbo:MusicalWork dbo:Artwork dbo:Film dbo:TelevisionShow dbo:TelevisionSeason dbo:TelevisionEpisode dbo:Poem dbo:Book dbo:Comic dbo:Play dbo:Group} #dbo:Person dbo:WrittenWork dbo:RadioProgram 
                    ?entity foaf:isPrimaryTopicOf wikipedia-en:"""+query_url+""";
                            dbo:wikiPageWikiLink ?dbEntities;
                            rdf:type ?mainEntityType .
                    ?dbEntities rdf:type ?type;
                            foaf:isPrimaryTopicOf ?wikiLinks;
                            rdfs:label ?label.
                    FILTER(langMatches(lang(?label),"EN"))
                    }
            """
            sparql = SPARQLWrapper("http://dbpedia.org/sparql")
            sparql.setReturnFormat(JSON)
            sparql.setQuery(db_query)
            db_res = sparql.query().convert()['results']['bindings']

            db_type = db_res[0]['mainEntityType']['value'].replace('http://dbpedia.org/ontology/', '')
            if db_type == 'MusicalWork':
                db_type = self.get_musical_entity_type(query_url)
            self.entities[cw]['dbpedia-type'] = db_type
            links = [i['wikiLinks']['value'].replace('http://en.wikipedia.org', '') for i in db_res]
            classes = [i['type']['value'].replace('http://dbpedia.org/ontology/', '') for i in db_res]
            db_uri = [i['dbEntities']['value'] for i in db_res]
            label = [i['label']['value'] for i in db_res]
            wld = {}
            ent_id = 0
            for link in links:
                for li in self.entities[cw]['li_tags']:
                    a_tags = li.find_all('a')
                    for a in a_tags:
                        href = a.get('href')
                        if href == link or urllib.parse.unquote(href) == link or re.sub(r'#.+', '', href) == link: #I use the unquote function to convert the %20 in the link to spaces
                            ls = str(a)
                            if ls not in wld:
                                ent_id += 1
                                wld[ls] = {"wikipedia-link": link, "text": [], "entity-id": "Entity-"+str(ent_id), 'class': classes[links.index(link)], 'label': label[links.index(link)],'db_uri': db_uri[links.index(link)]}
                            if a.text not in wld[ls]["text"]:
                                wld[ls]['text'].append(a.text)
            self.entities[cw]['wiki_links'] = wld

        for cw in self.entities:
            fast_check = {}
            for k in self.entities[cw]['wiki_links']:
                fast_check[self.entities[cw]['wiki_links'][k]['entity-id']] = (self.entities[cw]['wiki_links'][k]['wikipedia-link'] , self.entities[cw]['wiki_links'][k]['class'], self.entities[cw]['wiki_links'][k]['db_uri'], self.entities[cw]['wiki_links'][k]['label'])
            self.entities[cw]['fast-check'] = fast_check
        return self.entities


    def replace_entity_names(self):
        for cw in self.entities:
            to_parse = []
            src_to_parse = [] #will be reused to store the source string in the final graph
            for li in self.entities[cw]['li_tags']: 
                str_li = str(li)
                src_li = re.sub(r'<.+?>', '', str_li)
                src_li = re.sub(r'\[[0-9]+\]', ' ', src_li)
                src_to_parse.append(src_li)
                for k in self.entities[cw]['wiki_links']:
                    if k in str_li:
                        str_li  = str_li.replace(k, self.entities[cw]['wiki_links'][k]['entity-id'])
                        
                str_li = re.sub(r'<.+?>', '', str_li)
                str_li = re.sub(r'\[[0-9]+\]', ' ', str_li) #remove the numbers in square brackets (wikipedia references)
                to_parse.append(str_li)
            to_parse_txt = ' '.join(to_parse)
            self.entities[cw]['to_parse'] = to_parse
            self.entities[cw]['to_parse_txt'] = to_parse_txt
        return self.entities
    

    def scrape(self):
        self.get_wikipedia_url()
        self.scrape_wikipedia_page()
        self.get_wiki_links()
        self.replace_entity_names()
        return self.entities


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________



class RelationExtractor(object):
    GOOGLEBARD_TOKEN = os.getenv('GOOGLEBARD_TOKEN')
    lemma_synset_map = [('base', 'establish.v.08', 'based on'), ('inspire', 'inspire.v.02', 'inspired by'),
                             ('influence', 'determine.v.02', 'influenced by'), ('derive', 'derive.v.04', 'derived from'),
                             ('adapt', 'adapt.v.01', 'adapted from'), ('reference', 'reference.v.01', 'references'),
                             ('allude', 'allude.v.01', 'alludes to'), ('mention', 'mention.v.01', 'mentions'),
                             ('quote', 'quote.v.01', 'quotes')]
    
    entity_relation_map = {
            r'based\son': 'based on',
            r'inspired\sby': 'inspired by',
            r'influenced\sby': 'influenced by',
            r'derive[ds](\sfrom)?': 'derived from',
            r'adapted(\sfrom)?': 'adapted from',
            r'reference(s|d)?\s?(by|in)?': 'references',
            r'mention(s|ed\s(by|in)?)?': 'mentions',
            r'alludes?(\sto)?': 'alludes to',
            r'quotes?(\sto)?': 'quotes'
        }


    def __init__(self, entities_dict):
        self.entities = entities_dict

    

    def adjust_relations_to_type(self, entities):
        for cw in entities:
            entity_relations = entities[cw]['entity-relations']
            for ent in entity_relations:
                if entities[cw]['fast-check'][ent][1] in {'Artist', 'Group'}:
                    if entity_relations[ent] not in {'general influence', 'influenced by', 'inspired by'}:
                        entity_relations[ent] = 'general influence'
        return entities
    

#Google Bard approach
#_______________________________________
#_______________________________________

    def get_relations_bard(self):
        bard = Bard(token=self.GOOGLEBARD_TOKEN)
        for cw in self.entities:
            bard_res = bard.get_answer("You are an expert in relation extraction from plain text and your aim is to identify the existing relations between the creative work '"+cw+"', which is the implicit subject of the text you will be fed with, and other ENTITIES that you will find in the text. ### Return the relationships between '"+cw+"' and the entities marked as 'Entity- ' in the text in the following format: subject | relation | "+cw+" as a pandas dataframe following this example: ```df = pd.DataFrame({'Entity': ['Entity-', 'Entity-', 'Entity-'], 'Relation': ['based on', 'derived from', 'inspired by'], '"+cw+"': '"+cw+"' })```. ### Text: "+self.entities[cw]['to_parse_txt'])
            out_list = bard_res['content'].replace('\n\n', ' ').replace('\n', ' ').replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').split('```')
            for el in out_list:
                if 'df = pd.DataFrame' in el:
                    df_idx = out_list.index(el)
            df_string = re.sub(r'(python)\s?import pandas as pd (.+)\s?\=', '', out_list[df_idx])
            df_string = re.sub(r'print\(.+\)', '', df_string).strip()
            self.entities[cw]['entity-relations'] = eval(df_string).to_dict()
        return self.entities


    def group_entities(self):
        for cw in self.entities:
            groups = {}
            count = 0
            for sent in self.entities[cw]['to_parse']:
                g = re.findall(r'Entity-[0-9]+', sent)
                if g:
                    groups[count] = g
                count += 1
            self.entities[cw]['entity-groups'] = groups
        return self.entities
    

    def assign_missing_relations(self):
        for cw in self.entities:
            entity_relation = {}
            df = pd.DataFrame(self.entities[cw]['entity-relations'])
            for ent in df.values:
                relation = df[df['Entity'] == ent[0]]['Relation'].values[0]
                entity_relation[ent[0]] = relation
                for group in self.entities[cw]['entity-groups']:
                    if ent[0] in self.entities[cw]['entity-groups'][group]:
                        for e in self.entities[cw]['entity-groups'][group]:
                            if e not in df['Entity'].values:
                                entity_relation[e] = relation
            self.entities[cw]['entity-relations'] = entity_relation
        return self.entities
    

    def disambiguate_relations(self):
        for cw in self.entities:
            entity_relations = self.entities[cw]['entity-relations']
            for ent in entity_relations:
                relation_text = entity_relations[ent]
                for regex, relation_label in self.entity_relation_map.items():
                    if re.search(regex, relation_text):
                        entity_relations[ent] = relation_label
                        break
                    else:
                        pos = nlp(entity_relations[ent])
                        for tok in pos:
                            if tok.pos_ == 'VERB':
                                lemma = tok.lemma_
                                best_syn = ['general influence', 0]
                                for syn_a in self.lemma_synset_map:
                                    for syn_b in wn.synsets(lemma, pos=wn.VERB):
                                        similarity = wn.lch_similarity(wn.synset(syn_a[1]), wn.synset(syn_b.name()))
                                        if similarity >= 2.5 and similarity >= best_syn[1]:
                                            best_syn = [syn_a[2], similarity]
                                entity_relations[ent] = best_syn[0]
                            else:
                                entity_relations[ent] = 'general influence'

                            if entity_relations[ent] != 'general influence':
                                break
                        entity_relations[ent] = 'general influence'

        self.entities = self.adjust_relations_to_type(self.entities)
        return self.entities
            

#RB approach
#_______________________________________
#_______________________________________

    def store_relations_rb(self, rel_sent, relations): 
        if len(rel_sent) == 1: #if there is only one sentence in the list
            for k in rel_sent: #for every dictionary in the list
                if len(k['entities']) > 0: #if the dictionary contains at least one entity
                    if len(k['verbs']) == 1: #if the dictionary contains only one verb
                        for ent in k['entities']: #for every entity in the dictionary
                            relations[ent] = k['verbs'][0] #add the verb to the dictionary of relations
                    elif len(k['verbs']) == 0: #if the dictionary contains no verbs
                        for ent in k['entities']: #for every entity in the dictionary
                            relations[ent] = 'general influence' #add the general relation to the dictionary of relations
        elif len(rel_sent) > 1: #if there is more than one sentence in the list
            for k in rel_sent: #for every dictionary in the list of dictionaries
                idx = rel_sent.index(k) #get the index of the dictionary in the list
                if len(k['entities']) > 0: #if the dictionary contains at least one entity
                    if len(k['verbs']) == 1: #if the dictionary contains only one verb 
                        for ent in k['entities']: #for every entity in the dictionary
                            relations[ent] = k['verbs'][0] #add the verb to the dictionary of relations 
                    elif len(k['verbs']) == 0 and idx+1 < len(rel_sent): #if the dictionary contains no verbs and the index is not the last one
                        if (len(rel_sent[idx+1]['entities']) > 0 and rel_sent[idx]['entities'] == rel_sent[idx+1]['entities'] and len(rel_sent[idx+1]['verbs']) == 1) or (len(rel_sent[idx+1]['entities']) == 0 and len(rel_sent[idx+1]['verbs']) == 1): #if the next dictionary contains at least one entity and the entities are the same as the previous dictionary and the next dictionary contains only one verb or if the next dictionary contains no entities and only one verb
                            for ent in k['entities']: #for every entity in the dictionary 
                                relations[ent] = rel_sent[idx+1]['verbs'][0] #add the verb of the next dictionary to the dictionary of relations 
                        else: #if the next dictionary does not contain at least one entity or the entities are not the same as the previous dictionary or the next dictionary contains more than one verb
                            for ent in k['entities']: #for every entity in the dictionary
                                relations[ent] = 'general influence' #add the general relation to the dictionary of relations
                    else:
                        for ent in k['entities']: #for every entity in the dictionary
                            relations[ent] = k['verbs'] #add the verbs to the dictionary of relations
                else: #if the dictionary does not contain at least one entity
                    continue #the previous step should be able to handle this case too
        
        return relations
        

    def get_relations_rb(self):
        for cw in self.entities:
            rel_sent = []
            relations = {}
            last = False

            for s in self.entities[cw]['to_parse']: # for every sentence in the list of sentences containing the entity
                s_idx = self.entities[cw]['to_parse'].index(s) # get the index of the sentence in the list
                if s_idx + 1 == len(self.entities[cw]['to_parse']): # if the sentence is the last one
                    last = True # set the boolean to true 

                relations = self.store_relations_rb(rel_sent, relations) # call the function to store the relations in the dictionary
                            
                doc = nlp(s) #create a spacy doc from the sentence
                rel_sent = [] #reset the list of dictionaries

                for sent in doc.sents: #for every sentence in the doc (in case the sentence is a complex sentence)
                    cand_ent = set() #set of candidate entities in the sentence
                    cand_verbs = set() #set of candidate verbs in the sentence 
                    current_verb = '' #string to store the current verb
                    lemma = '' #string to store the lemma of the current verb
                    next_tok = False # boolean to check if it is necessary to check the next token 
                    for token in sent: #for every token in the sentence 
                        #print(token.text, token.pos_, token.dep_)
                        if token.text in self.entities[cw]['fast-check']: #if the token is an entity found in the wikipedia page
                            cand_ent.add(token.text) #add the entity to the set of candidate entities 
                        elif token.pos_ == 'VERB' and token.lemma_ not in {"be", "have", "do"}: #if the token is a verb
                            current_verb = token.text #store the verb in the string of the current verb
                            lemma = token.lemma_ #store the lemma of the verb in the string of the lemma
                            next_tok = True #set the boolean to true to check the next token
                        else:
                            if next_tok: #if it is a "next token"
                                if token.dep_ == 'prep' or token.dep_ == 'agent': #if the token is a preposition or an agent 
                                    next_tok = False #set the boolean to false 
                                    current_verb += ' ' + token.text #add the token to the string of the current verb
                                    cand_verbs.add((current_verb, lemma)) #add the tuple of the current verb and its lemma to the set of candidate verbs
                                    current_verb = '' #reset the string of the current verb
                                else:
                                    next_tok = False #set the boolean to false
                                    cand_verbs.add((current_verb, lemma)) #add the tuple of the current verb and its lemma to the set of candidate verbs
                                    current_verb = '' #reset the string of the current verb

                    if cand_verbs: #if the set of candidate verbs is not empty
                        sel_ve = [] #list of selected verbs 
                        for tup in cand_verbs: #for every tuple in the set of candidate verbs
                            assigned = False
                            for regex, relation_label in self.entity_relation_map.items(): 
                                    if re.search(regex, tup[0]):
                                        sel_ve.append((tup[0], relation_label))
                                        assigned = True 
                                        break
                            if not assigned:
                                if re.match(r'based\son|(inspired|influenced)(\sby)?|(derive[ds]?|adapted)(\sfrom)?|(reference|mention)(s|ed\s(by|in)?)?|alludes?\sto|quote[sd]?', tup[0]): #if the verb matches one of the regular expressions
                                    sel_ve.append(tup) #add the tuple to the list of selected verbs
                                else:
                                    sel_ve.append((tup[0], 'general influence')) #add the tuple of the verb and the general influence to the list of selected verbs

                    if cand_ent or sel_ve: #if the set of candidate entities or the list of selected verbs is not empty
                        ev_dict = {'entities': [], 'verbs': []} #create a dictionary to store the entities and the verbs

                        for ent in cand_ent: #for every entity in the set of candidate entities
                            if ent not in ev_dict['entities']: #if the entity is not already in the dictionary
                                ev_dict['entities'].append(ent) #add the entity to the dictionary

                        
                        for verb in sel_ve: #for every tuple in the list of selected verbs
                            if verb[1] not in ev_dict['verbs']: #if the lemma of the verb is not already in the dictionary
                                ev_dict['verbs'].append(verb[1]) #add the lemma of the verb to the dictionary
                    
                        rel_sent.append(ev_dict) #add the dictionary to the list of dictionaries

                if last: #if it is the last sentence
                    relations = self.store_relations_rb(rel_sent, relations) #call the function to store the relations in the dictionary

        for ent in relations:
            if type(relations[ent]) == list :
                if len(relations[ent]) > 1 and 'general influence' in relations[ent]:
                    relations[ent].remove('general influence')
                relations[ent] = relations[ent][0]
            for lemma_rel in self.lemma_synset_map:
                if lemma_rel[0] == relations[ent]:
                    relations[ent] = lemma_rel[2]
        
        self.entities[cw]['entity-relations'] = relations
        self.entities = self.adjust_relations_to_type(self.entities)

        return self.entities




    def extract_relations(self):
        try:
            self.get_relations_bard()
            self.group_entities()
            self.assign_missing_relations()
            self.disambiguate_relations()
        except:
            self.get_relations_rb()
            self.group_entities()

        return self.entities


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________



class KnowledgeGraphPopulator(object):
    # Namespaces
    core = Namespace("https://w3id.org/polifonia/ontology/core/")
    mm = Namespace("https://w3id.org/polifonia/ontology/music-meta/")
    prov = Namespace("http://www.w3.org/ns/prov#")
    mucho = Namespace("https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#")
    # Classes
    Agent = core.Agent
    MusicEnsenble  = mm.MusicEnsenble
    Person = core.Person
    Musician = mm.Musician
    InformationObject = core.InformationObject
    AudiovisualEntity = mucho.AudiovisualEntity
    LiteraryEntity = mucho.LiteraryEntity
    VisualArtEntity = mucho.VisualArtEntity
    MusicEntity = mm.MusicEntity
    MusicAlbum = mucho.MusicAlbum
    Song = mucho.Song
    MusicArtist = mm.MusicArtist
    MusicGenre = mm.MusicGenre
    Influence = prov.Influence
    EntityInfluence = prov.EntityInfluence
    Inspiration = mucho.Inspiration
    Derivation = prov.Derivation
    Adaptation = mucho.Adaptation
    Basis = mucho.Basis
    Reference = mucho.Reference
    Allusion = mucho.Allusion
    Citation = mucho.Citation
    Mention = mucho.Mention
    Text = mm.Text
    Lyrics = mm.Lyrics
    TextFragment = mm.TextFragment
    Annotation = mucho.Annotation

    # Object properties
    hasInformationSource = mucho.hasInformationSource
    hasAuthor = mucho.hasAuthor
    isAuthorOf = mucho.isAuthorOf
    hasGenre = mm.hasGenre
    isGenreOf = mm.isGenreOf
    hasMember = core.hasMember
    isMemberOf = core.isMemberOf
    hasPart = core.hasPart
    isPartOf = core.isPartOf
    hasMusicEntityPart = mm.hasMusicEntityPart
    isPartOfMusicEntity = mm.isPartOfMusicEntity
    isTextFragmentOf = mm.isTextFragmentOf
    hasTextFragment = mm.hasTextFragment
    hasSource = mm.hasSource
    influenced = prov.influenced
    influencer = prov.influencer
    entity = prov.entity
    qualifiedInfluence = prov.qualifiedInfluence
    qualifiedDerivation = prov.qualifiedDerivation
    qualifiedAdaptation = mucho.qualifiedAdaptation
    qualifiedBasis = mucho.qualifiedBasis
    qualifiedReference = mucho.qualifiedReference
    qualifiedAllusion = mucho.qualifiedAllusion
    qualifiedCitation = mucho.qualifiedCitation
    qualifiedMention = mucho.qualifiedMention
    qualifiedInspiration = mucho.qualifiedInspiration
    wasInfluencedBy = prov.wasInfluencedBy
    wasDerivedFrom = prov.wasDerivedFrom
    isAdaptationOf = mucho.isAdaptationOf
    isBasedOn = mucho.isBasedOn
    references = mucho.references
    alludesTo = mucho.alludesTo
    cites = mucho.cites
    mentions = mucho.mentions
    wasInspiredBy = mucho.wasInspiredBy
    hasAnnotation = mucho.hasAnnotation
    isAnnotationOf = mucho.isAnnotationOf

    # Data properties
    influenceInformation = mucho.influenceInformation
    influenceInformationSource = mucho.influenceInformationSource
    influenceSourceText = mucho.influenceSourceText
    name = core.name
    nickname = core.nickname
    text = core.text
    title = core.title


    def __init__(self, song_dict, entities_dict):
        self.song = song_dict
        self.entities = entities_dict
        self.mucho_gustore = Graph()


    def get_musical_work_type(self, entity_id):
        q_type = """
                    PREFIX dbo: <http://dbpedia.org/ontology/>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        
                    SELECT ?type
                    WHERE { 
                            VALUES ?type { dbo:Album dbo:Song dbo:Single }
                            <"""+entity_id+"""> rdf:type ?type.
                            }
                """

        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setReturnFormat(JSON)
        sparql.setQuery(q_type)
        ent_type = sparql.query().convert()['results']['bindings'][0]['type']['value'].replace('http://dbpedia.org/ontology/', '')
        if ent_type == 'Album':
            return 'Album'
        elif ent_type == 'Single' or ent_type == 'Song':
            return 'Song'
        else:
            return 'MusicEntity'


    def add_song_data(self):
        song_uri = URIRef('https://musicbrainz.org/recording/'+self.song['musicbrainz_id'])
        base_indv = 'https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#'

        # Add song
        self.mucho_gustore.add((song_uri, RDF.type, self.Song))
        self.mucho_gustore.add((song_uri, self.title, Literal(self.song['name'], datatype=XSD.string, normalize=False)))
        self.mucho_gustore.add((song_uri, RDFS.label, Literal(self.song['name'], datatype=XSD.string, normalize=False)))

        # Add song lyrics
        lyrics_bn = BNode()
        self.mucho_gustore.add((song_uri, self.hasPart, lyrics_bn))
        self.mucho_gustore.add((lyrics_bn, RDF.type, self.Lyrics))
        self.mucho_gustore.add((lyrics_bn, self.text, Literal(self.song['lyrics'], datatype=XSD.string, normalize=False)))

        # Add text fragments and annotations to the lyrics
        for ann_num, ann in enumerate(self.song['annotations']):
            fr_name = base_indv+'fragment_'+str(ann_num)
            ann_name = base_indv+'annotation_'+str(ann_num)
            self.mucho_gustore.add((lyrics_bn, self.hasTextFragment, URIRef(fr_name)))
            self.mucho_gustore.add((URIRef(fr_name), RDF.type, self.TextFragment))
            self.mucho_gustore.add((URIRef(fr_name), self.text, Literal(ann[0].replace('\n\n', '\n'), datatype=XSD.string, normalize=False)))
            self.mucho_gustore.add((URIRef(fr_name), self.hasAnnotation, URIRef(ann_name)))
            self.mucho_gustore.add((URIRef(ann_name), RDF.type, self.Annotation))
            self.mucho_gustore.add((URIRef(ann_name), self.text, Literal(ann[1].replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))


        # Add song artists
        for art in self.song['artists']:
            if 'wikidata_url' in art:
                art_uri = URIRef(art['wikidata_url'])
            else:
                art_uri = URIRef('https://musicbrainz.org/artist/'+self.song['artists'][art]['mbz_id'])

            self.mucho_gustore.add((song_uri, self.hasAuthor, art_uri))
            self.mucho_gustore.add((art_uri, self.name, Literal(art['name'], datatype=XSD.string, normalize=False)))
            self.mucho_gustore.add((art_uri, RDFS.label, Literal(art['name'], datatype=XSD.string, normalize=False)))

            if art['type'] == 'Group':
                self.mucho_gustore.add((art_uri, RDF.type, self.MusicEnsenble))
            elif art['type'] == 'Person':
                self.mucho_gustore.add((art_uri, RDF.type, self.Musician))

            # Add artists genres
            for genre in self.song['artists'][art]['genres']:
                genre = genre.replace(' ', '_')
                genre_uri = URIRef(base_indv+genre)
                self.mucho_gustore.add((art_uri, self.hasGenre, genre_uri))
                self.mucho_gustore.add((genre_uri, RDF.type, self.MusicGenre))
                self.mucho_gustore.add((genre_uri, RDFS.label, Literal(genre, datatype=XSD.string, normalize=False)))

        return True
    

    def add_cw_data(self):
        # Add relation with referenced creative work
        song_uri = URIRef('https://musicbrainz.org/recording/'+self.song['musicbrainz_id'])
        base_indv = 'https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#'

        for woa in self.entities:
            woa_uri = URIRef('https://www.wikidata.org/wiki/'+ self.entities[woa]['id'])
            self.mucho_gustore.add((song_uri, self.references, woa_uri))
            self.mucho_gustore.add((woa_uri, self.title, Literal(woa, datatype=XSD.string, normalize=False)))
            self.mucho_gustore.add((woa_uri, RDFS.label, Literal(woa, datatype=XSD.string, normalize=False)))
            # Add reference information
            reference_bn = BNode()
            self.mucho_gustore.add((song_uri, self.qualifiedReference, reference_bn))
            self.mucho_gustore.add((reference_bn, RDF.type, self.Reference))
            self.mucho_gustore.add((reference_bn, self.entity, woa_uri))

            woa_type = self.entities[woa]['dbpedia-type']

            if woa_type == 'MusicalWork':
                self.mucho_gustore.add((woa_uri, RDF.type, self.MusicEntity))
            elif woa_type == 'Album':
                self.mucho_gustore.add((woa_uri, RDF.type, self.MusicAlbum))
            elif woa_type == 'Single' or woa_type == 'Song':
                self.mucho_gustore.add((woa_uri, RDF.type, self.Song))
            elif woa_type == 'Artwork':
                self.mucho_gustore.add((woa_uri, RDF.type, self.VisualArtEntity))
            elif woa_type == 'Film' or woa_type == 'TelevisionShow' or woa_type == "TelevisionSeason" or woa_type == 'TelevisionEpisode':
                self.mucho_gustore.add((woa_uri, RDF.type, self.AudiovisualEntity))
            elif woa_type == 'Poem' or woa_type == 'Book' or woa_type == 'Comic' or woa_type == 'Play':
                self.mucho_gustore.add((woa_uri, RDF.type, self.LiteraryEntity))
            else:
                self.mucho_gustore.add((woa_uri, RDF.type, self.InformationObject))


            # Add source url and information text about relation
            for ref_woa in self.song['referenced-creative-works']:
                if ref_woa == woa:
                    for a in self.song['referenced-creative-works'][ref_woa]["annotation_number"]:
                        string = self.song["annotations"][int(a)][1].replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' ')
                        self.mucho_gustore.add((reference_bn, self.influenceSourceText, Literal(string, datatype=XSD.string, normalize=False)))
                        self.mucho_gustore.add((reference_bn, self.hasInformationSource, URIRef(base_indv+'annotation_'+str(a)))) #add the annotation as information source for the relation
            self.mucho_gustore.add((reference_bn, self.influenceInformationSource, Literal(self.song['genius_url'], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))

        return True


    def add_linked_entities_data(self):
        for woa in self.entities:
            woa_uri = URIRef('https://www.wikidata.org/wiki/'+ self.entities[woa]['id'])
            # Add relations with other creative works
            for ent in self.entities[woa]['entity-relations']:
                ent_uri = URIRef(self.entities[woa]['fast-check'][ent][2])
                ent_type = self.entities[woa]['fast-check'][ent][1]
                #Add entity type
                if ent_type == 'MusicalWork':
                    db_et_query = """
                    PREFIX dbo: <http://dbpedia.org/ontology/>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        
                    SELECT ?type
                    WHERE { 
                            VALUES ?type { dbo:Album dbo:Song dbo:Single }
                            <"""+self.entities[woa]['fast-check'][ent][2]+"""> rdf:type ?type.
                            }
                    """

                    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
                    sparql.setReturnFormat(JSON)
                    sparql.setQuery(db_et_query)
                    ent_type = sparql.query().convert()['results']['bindings'][0]['type']['value'].replace('http://dbpedia.org/ontology/', '')
                    if ent_type == 'Album':
                        self.mucho_gustore.add((ent_uri, RDF.type, self.MusicAlbum))
                    elif ent_type == 'Single' or ent_type == 'Song':
                        self.mucho_gustore.add((ent_uri, RDF.type, self.Song))
                    else:
                        self.mucho_gustore.add((ent_uri, RDF.type, self.MusicEntity))
                    self.mucho_gustore.add((ent_uri, self.title, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False))) #I repeat this line for every condiftional block because in some cases the property changes 
                elif ent_type == 'Artwork':
                    self.mucho_gustore.add((ent_uri, RDF.type, self.VisualArtEntity))
                    self.mucho_gustore.add((ent_uri, self.title, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False)))
                elif ent_type == 'Film' or ent_type == 'TelevisionShow' or ent_type == "TelevisionSeason" or ent_type == 'TelevisionEpisode':
                    self.mucho_gustore.add((ent_uri, RDF.type, self.AudiovisualEntity))
                    self.mucho_gustore.add((ent_uri, self.title, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False)))
                elif ent_type == 'Poem' or ent_type == 'Book' or ent_type == 'Comic' or ent_type == 'Play':
                    self.mucho_gustore.add((ent_uri, RDF.type, self.LiteraryEntity))
                    self.mucho_gustore.add((ent_uri, self.title, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False)))
                elif ent_type == 'Person':
                    self.mucho_gustore.add((ent_uri, RDF.type, self.Person))
                    self.mucho_gustore.add((ent_uri, self.name, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False)))
                elif ent_type == 'Group':
                    self.mucho_gustore.add((ent_uri, RDF.type, self.Group))
                    self.mucho_gustore.add((ent_uri, self.name, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False)))
                
                self.mucho_gustore.add((ent_uri, RDFS.label, Literal(self.entities[woa]['fast-check'][ent][3], datatype=XSD.string, normalize=False))) # In any case I add the label at the end

                
                # Add entity relation
                if self.entities[woa]['entity-relations'] == 'based on':
                    self.mucho_gustore.add((ent_uri, self.isBasedOn, woa_uri))
                    based_on_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedBasis, based_on_bn))
                    self.mucho_gustore.add((based_on_bn, RDF.type, self.Basis))
                    self.mucho_gustore.add((based_on_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((based_on_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((based_on_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'inspired by':
                    self.mucho_gustore.add((ent_uri, self.wasInspiredBy, woa_uri))
                    insp_by_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedInspiration, insp_by_bn))
                    self.mucho_gustore.add((insp_by_bn, RDF.type, self.Inspiration))
                    self.mucho_gustore.add((insp_by_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((insp_by_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((insp_by_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'derived from':
                    self.mucho_gustore.add((ent_uri, self.wasDerivedFrom, woa_uri))
                    der_from_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedDerivation, der_from_bn))
                    self.mucho_gustore.add((der_from_bn, RDF.type, self.Derivation))
                    self.mucho_gustore.add((der_from_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((der_from_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((der_from_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'adapted from':
                    self.mucho_gustore.add((ent_uri, self.isAdaptationOf, woa_uri))
                    ad_of_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedAdaptation, ad_of_bn))
                    self.mucho_gustore.add((ad_of_bn, RDF.type, self.Adaptation))
                    self.mucho_gustore.add((ad_of_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((ad_of_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((ad_of_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'references':
                    self.mucho_gustore.add((ent_uri, self.references, woa_uri))
                    ref_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedReference, ref_bn))
                    self.mucho_gustore.add((ref_bn, RDF.type, self.Reference))
                    self.mucho_gustore.add((ref_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((ref_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((ref_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'mentions':
                    self.mucho_gustore.add((ent_uri, self.mentions, woa_uri))
                    men_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedMention, men_bn))
                    self.mucho_gustore.add((men_bn, RDF.type, self.Mention))
                    self.mucho_gustore.add((men_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((men_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((men_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'alludes to':
                    self.mucho_gustore.add((ent_uri, self.alludesTo, woa_uri))
                    all_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedAllusion, all_bn))
                    self.mucho_gustore.add((all_bn, RDF.type, self.Allusion))
                    self.mucho_gustore.add((all_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((all_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((all_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                elif self.entities[woa]['entity-relations'] == 'quotes':
                    self.mucho_gustore.add((ent_uri, self.cites, woa_uri))
                    cit_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedCitation, cit_bn))
                    self.mucho_gustore.add((cit_bn, RDF.type, self.Citation))
                    self.mucho_gustore.add((cit_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((cit_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            self.mucho_gustore.add((cit_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))

                else: # entity_relation[ent] == 'influenced by' or entity_relation[ent] == 'general influence'
                    self.mucho_gustore.add((ent_uri, self.wasInfluencedBy, woa_uri))
                    inf_by_bn = BNode()
                    self.mucho_gustore.add((ent_uri, self.qualifiedInfluence, inf_by_bn))
                    self.mucho_gustore.add((inf_by_bn, RDF.type, self.EntityInfluence))
                    self.mucho_gustore.add((inf_by_bn, self.entity, woa_uri))
                    self.mucho_gustore.add((inf_by_bn, self.influenceInformationSource, Literal(self.entities[woa]["wikipedia_url"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#anyURI"))))
                    for gr in self.entities[woa]['entity-groups']:
                        if ent in self.entities[woa]['entity-groups'][gr]:
                            source_sent = self.entities[woa]['to_parse'][gr]
                            for ent_g in self.entities[woa]['entity-groups'][gr]:
                                if ent_g in source_sent:
                                    source_sent = source_sent.replace(ent_g, self.entities[woa]['fast-check'][ent][3])
                            
                            self.mucho_gustore.add((inf_by_bn, self.influenceSourceText, Literal(source_sent.replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' '), datatype=XSD.string, normalize=False)))
        
        return True
    


    def serialize(self):
        self.mucho_gustore.serialize(destination='./knowledge_graphs/'+self.song['spotify-id']+'.ttl', format='turtle')
        return self.mucho_gustore
    

    def populate_graph(self):
        self.add_song_data()
        self.add_cw_data()
        self.add_linked_entities_data()
        knowledge_graph = self.serialize()
        return knowledge_graph
    




class MuchEx(object):
    def __init__(self):
        pass

    def run(self, song_id):
        song_data = SongDataCollector(song_id).get_song_data()
        #print('______SONG DATA______')
        #print(song_data)

        annotations = song_data['annotations']
        information_extractor = InformationExtractor(annotations, song_data)
        
        creative_works, people = information_extractor.extract_information()
        if not creative_works:
            return "\n\n-------------------\nNo creative work has been found to be extracted.\n-------------------\n\n"
        #print('______INFORMATION EXTRACTOR______')
        #print(creative_works, people)

        candidate_extractor = CandidateExtractor(creative_works)
        candidates = candidate_extractor.get_candidates()
        #print('______CANDIDATE EXTRACTOR______')
        #print(candidates)

        disambiguator = Disambiguator(people, candidates, annotations)
        entities_data = disambiguator.disambiguate()
        #print('______DISAMBIGUATOR______')
        #print(entities_data)

        scraper = Scraper(entities_data)
        entities_data = scraper.scrape()
        #print('______SCRAPER______')
        #print(entities_data)

        relation_extractor = RelationExtractor(entities_data)
        entities_data = relation_extractor.extract_relations()
        #print('______RELATION EXTRACTOR______')
        #print(entities_data)

        # The cited creative works and people are stored inside the song_data dictionary to be passed as input for the graph population
        song_data['referenced-creative-works'] = creative_works
        song_data['cited-people'] = people

        #print('\n\n\n\n______SONG DATA______\n\n')
        #print(song_data)

        graph_populator = KnowledgeGraphPopulator(song_data, entities_data)
        kg = graph_populator.populate_graph()
        #print('______GRAPH POPULATOR______')
        #print(kg)

        return kg
