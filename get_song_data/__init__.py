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

nlp = en_core_web_sm.load()
load_dotenv()


class SongDataCollector(object):

    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')
    MUSICBRAINZ_USER = os.getenv('MUSICBRAINZ_USER')
    MUSICBRAINZ_TOKEN = os.getenv('MUSICBRAINZ_TOKEN')


    def __init__(self, spotify_id):
        self.spotify_id = spotify_id

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


    def get_spotify_song(self, headers=None):
        # Get song data from Spotify API
        if headers == None:
            headers = self.get_spotify_headers()
        return requests.get(f'https://api.spotify.com/v1/tracks/{self.spotify_id}', headers=headers).json()


    def get_spotify_artist(self, artist_id, headers=None):
        # Get song data from Spotify API
        if headers == None:
            headers = self.get_spotify_headers()
        return requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers).json()



    def save_spotify_data(self):
        # Save song data from Spotify API
        song = {}
        headers = self.get_spotify_headers()
        song_data = self.get_spotify_song(headers)
        song['spotify_id'] = song_data['id']
        song['spotify_href'] = song_data['href']
        song['name'] = song_data['name']
        song['artists'] = []
        for artist in song_data['artists']:
            artist_dict = {}
            artist_dict['spotify_id'] = artist['id']
            artist_dict['spotify_href'] = artist['href']
            artist_dict['name'] = artist['name']
            get_art =  self.get_spotify_artist(artist['id'], headers)
            artist_dict['genres'] = get_art['genres']
            song['artists'].append(artist_dict)
        song['isrc'] = song_data['external_ids']['isrc']

        return song



#_______________________________________________________
# Genius API
#_______________________________________________________

    def get_genius_data(self, song_name, artist_name):
        # Get song data from Genius API
        genius = Genius(self.GENIUS_ACCESS_TOKEN)
        return genius.search_song(song_name, artist_name)



    def save_genius_data(self, song_name, artist_name, store=dict()):
        genius = Genius(self.GENIUS_ACCESS_TOKEN)
        genius_song = self.get_genius_data(song_name, artist_name)
        genius_id = genius_song.id

        store['genius_id'] = genius_id
        store['genius_url'] = genius_song.url
        store['lyrics'] = re.sub(r'[0-9]+\sContributors.+\sLyrics\n', '', genius.lyrics(genius_id, remove_section_headers=True))
        
        annotations_list = []
        annotations = genius.song_annotations(genius_id)
        for tup in annotations:
            new_tup = (tup[0], tup[1][0][0])
            annotations_list.append(new_tup)
        store['annotations'] = annotations_list

        return store

#_______________________________________________________
# MusicBrainz API
#_______________________________________________________ 

    def get_musicbrainz_song(self, user_agent, version, isrc, auth=False):
        # Get song data from MusicBrainz API
        if auth:
            mbz.set_useragent(user_agent, version)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        mbz_song = mbz.get_recordings_by_isrc(isrc)
        return mbz.get_recording_by_id(mbz_song['isrc']['recording-list'][0]['id'], includes=['artists'])
    

    def get_musicbrainz_artist(self, user_agent, version, art_id, auth=False):
        # Get artist data from MusicBrainz API
        if auth:
            mbz.set_useragent(user_agent, version)
            mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)
        return mbz.get_artist_by_id(art_id, includes=["url-rels", "tags"])

    
    def save_musicbrainz_data(self, user_agent, version, isrc, store=dict()):
        # Save song data from MusicBrainz API
        mbz.set_useragent(user_agent, version)
        mbz.auth(self.MUSICBRAINZ_USER, self.MUSICBRAINZ_TOKEN)

        mbz_song = self.get_musicbrainz_song(user_agent, version, isrc)
        if 'artists' not in store:
            art_dict = {}
            for artist in mbz_song['artist-credit']:
                art_dict['name'] = artist['artist']['name']
                art_dict['mbz_id'] = artist['artist']['id']
                art_dict['disambiguation'] = artist['artist']['disambiguation']
                #art_dict['tags'] = artist['artist']['tags']
            store['artists'] = art_dict
        else:
            for art in store['artists']: #for every artist in the song_ditionary
                for mbz_art in mbz_song['recording']['artist-credit']:   #for every artist in the mbz dictionary
                    if art['name'] == mbz_art['artist']['name']:   #if the name of the artist in the song dictionary is the same as the name of the artist in the mbz dictionary
                        art['disambiguation'] = mbz_art['artist']['disambiguation'] #add the disambiguation to the song dictionary
                        art['mbz_id'] = mbz_art['artist']['id'] #add the mbz id to the song dictionary
                        #art['mbz_tags'] = {}
                        #for tag in mbz_art['artist']['tag-list']: #for every tag in the mbz dictionary
                        #    art['mbz_tags'][tag['name']] = tag['count'] #add the tag name and the tag count to the song dictionary
                wts = self.get_musicbrainz_artist(user_agent, version, art['mbz_id'])
                art['type'] = wts['artist']['type']
                for url in wts['artist']['url-relation-list']:
                    if url['type'] == 'wikidata':
                        art['wikidata_url'] = url['target']
        return store


#_______________________________________________________
# Get all data
#_______________________________________________________

    def get_song_data(self, mbz_user_agent, mbz_app_version):
        # Get song data from all APIs
        song_data = self.save_spotify_data()
        song_data = self.save_genius_data(song_data['name'], song_data['artists'][0]['name'], song_data)
        song_data = self.save_musicbrainz_data(mbz_user_agent, mbz_app_version, song_data['isrc'], song_data)
        return song_data


#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________
#_______________________________________________________

class InformationExtractor(object):
    def __init__(self, annotation_list):
        self.annotation_list = annotation_list
        
    
    def get_entities(self):
        creative_works = {}
        people = {}
        for idx, annotation in enumerate(self.annotation_list):
            doc = nlp(annotation[1])
            for ent in doc.ents:
                if ent.label_ == 'WORK_OF_ART':
                    cw_sub_str = re.sub(r'[’\']s$', '', ent.text)
                    if cw_sub_str not in creative_works:
                        creative_works[cw_sub_str] = {'count': 0, 'annotation_number': {}}
                if ent.label_ == 'PERSON':
                    per_sub_str = re.sub(r'[’\']s$', '', ent.text)
                if per_sub_str not in people:
                    people[per_sub_str] = {'count': 0, 'annotation_number': {}}
                
        return creative_works, people
    
    def store_entities(self, creative_works, people):
        for ann_num, ann in enumerate(self.annotation_list):
            clean_txt = re.sub(r'\W', ' ', ann[1]) #remove all the non alphanumeric characters
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
    

class CandidateExtractor(object):
    def __init__(self, creative_works):
        self.creative_works = creative_works
    
    def wikidata_reconciliation(query):
        API_WD = "https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': 'en',
            'type': 'item',
            'search': query # the query string
        }
        
        # query wd API    
        return requests.get(API_WD, params = params).json()
    
    def get_candidates(self):
        candidates = {}
        for cw in self.creative_works:
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
                        entity['description'] = result['description']
                        candidates[cw].append(entity)
        
        return candidates
    

class Disambiguator(object):
    def __init__(self, people, candidates):
        self.people = people
        self.candidates = candidates

    def assign_scores(self):
        req = 0 # this is the number of requests made to the WD endpoint

        people = []
        for per in people:
            people.append((per, people[per]['count']))


        for cw in self.candidates:
            relevance = len(self.candidates[cw])

            for idx, cand in enumerate(self.candidates[cw]):

                cand['relevance'] = relevance 
                relevance -= 1 #decrease for the next iteration

                cand['dependency_score'] = 0  #this is the score that will be used to compute the dependency between candidates
                cand['person_in_description'] = 0 #this is the number of times the person is mentioned in the description of the candidate
                cand['person_in_wikidata'] = 0 #this is the number of times a person is mentioned in the wikidata page of the candidate
                
                for per in people:
                    per_split = per[0].split(' ')
                    if len(per_split) > 1:
                        per_ts = per_split[-1]  #take the last token of the person name [SI PUO' FARE MEGLIO INCLODENDO TUTTI I TOKEN DELLA PERSONA IN UN CICLO FOR E VEDERE SE SONO TUTTI IN DESCRIPTION ECC.]
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


    def get_clean_annotations(self, annotations):
        sents = []
        for ann in annotations:
            clean_txt = ann[1].replace('\n\n', ' ').replace('\n', ' ').replace('   ', ' ').replace('  ', ' ')
            sts = sent_tokenize(clean_txt)
            for s in sts:
                sents.append(s)
        return sents
    

    def get_sentence_similarity(self, annotations):
        to_embed = {}
        sents = self.get_clean_annotations(annotations)
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
    
    def scrape_wikipedia_page(self):
        for cw in self.entities:
            url = cw['wikipedia_url']

            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser").select('body')[0]
            spans = soup.find_all('span', string=[re.compile('^(Cultural)? [Ii]mpact$'), re.compile('^[Aa]daptations?')])

            h2_tags = [span.parent for span in spans if span.parent.name == 'h2']

            li_tags = []
            for h2 in h2_tags:
                for el in h2.next_siblings:
                    if el.name == 'h2':
                        break
                    if el.name == 'ul':
                        li_tags.extend(el.find_all('li'))
            
            cw['li_tags'] = li_tags

        return self.entities
    


    def get_entity_type(self):
        for cw in self.entities:
            url = cw['wikipedia_url']
            base_url = url.replace('https://en.wikipedia.org/wiki/', '')

            db_query_ent_type = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX wikipedia-en: <http://en.wikipedia.org/wiki/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT DISTINCT ?wikiLinks ?type
            WHERE { 
                    VALUES ?type { dbo:MusicalWork dbo:Artwork dbo:Film dbo:TelevisionShow dbo:TelevisionSeason dbo:TelevisionEpisode dbo:Poem dbo:Book dbo:Comic dbo:Play}
                    ?entity foaf:isPrimaryTopicOf wikipedia-en:"""+base_url+""";
                            rdf:type ?type.
                    }
            """
            sparql = SPARQLWrapper("http://dbpedia.org/sparql")
            sparql.setReturnFormat(JSON)
            sparql.setQuery(db_query_ent_type)
            
            cw_type = sparql.query().convert()['results']['bindings'][0]['type']['value'].replace('http://dbpedia.org/ontology/', '')

            if cw_type == 'MusicalWork':
                db_query_ent_type = """
                    PREFIX dbo: <http://dbpedia.org/ontology/>
                    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    PREFIX wikipedia-en: <http://en.wikipedia.org/wiki/>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                    SELECT DISTINCT ?wikiLinks ?type
                    WHERE { 
                            VALUES ?type { dbo:Album dbo:Song dbo:Single}
                            ?entity foaf:isPrimaryTopicOf wikipedia-en:"""+base_url+""";
                                    rdf:type ?type.
                            }
                    """

                sparql = SPARQLWrapper("http://dbpedia.org/sparql")
                sparql.setReturnFormat(JSON)
                sparql.setQuery(db_query_ent_type)

                cw_type = sparql.query().convert()['results']['bindings'][0]['type']['value'].replace('http://dbpedia.org/ontology/', '')
            
            cw['dbpedia-type'] = cw_type
        return self.entities



    def get_wiki_links(self):
        for cw in self.entities:
            url = cw['wikipedia_url']
            base_url = url.replace('https://en.wikipedia.org/wiki/', '')

            db_query = """
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX wikipedia-en: <http://en.wikipedia.org/wiki/>
            PREFIX schema: <http://schema.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX xml: <http://www.w3.org/XML/1998/namespace>

            SELECT DISTINCT ?wikiLinks ?type ?dbEntities ?label
            WHERE { 
                    VALUES ?type { dbo:Artist dbo:MusicalWork dbo:Artwork dbo:Film dbo:TelevisionShow dbo:TelevisionSeason dbo:TelevisionEpisode dbo:Poem dbo:Book dbo:Comic dbo:Play dbo:Group} #dbo:Person dbo:WrittenWork  dbo:RadioProgram 
                    ?entity foaf:isPrimaryTopicOf wikipedia-en:"""+base_url+""";
                            dbo:wikiPageWikiLink ?dbEntities.
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
            links = [i['wikiLinks']['value'].replace('http://en.wikipedia.org', '') for i in db_res]
            classes = [i['type']['value'].replace('http://dbpedia.org/ontology/', '') for i in db_res]
            db_uri = [i['dbEntities']['value'] for i in db_res]
            label = [i['label']['value'] for i in db_res]

            wld = {}
            ent_id = 0
            for link in links:
                for li in cw['li_tags']:
                    a_tags = li.find_all('a')

                    for a in a_tags:
                        href = a.get('href')
                        if href == link or urllib.parse.unquote(href) == link or re.sub(r'#.+', '', href) == link: #I use the unquote function to convert the %20 in the link to spaces
                            ls = str(a)
                            if ls not in wld:
                                ent_id += 1
                                wld[ls] = {"wikipedia link": link, "text": [], "entity id": "Entity-"+str(ent_id), 'class': classes[links.index(link)], 'label': label[links.index(link)],'db_uri': db_uri[links.index(link)]}
                            if a.text not in wld[ls]["text"]:
                                wld[ls]['text'].append(a.text)
            cw['wiki_links'] = wld

        
        for cw in self.entities:
            fast_check = {}
            for k in cw['wiki_links']:
                fast_check[cw['wiki_links'][k]['entity id']] = (cw['wiki_links'][k]['wikipedia link'] , cw['wiki_links'][k]['class'], cw['wiki_links'][k]['db_uri'], cw['wiki_links'][k]['label'])
            cw['fast-check'] = fast_check
    
        return self.entities


    def replace_entity_names(self):
        for cw in self.entities:
            to_parse = []
            src_to_parse = [] #will be reused to store the source string in the final graph

            for li in cw['li_tags']:
                str_li = str(li)
                src_li = re.sub(r'<.+?>', '', str_li)
                src_li = re.sub(r'\[[0-9]+\]', ' ', src_li)
                src_to_parse.append(src_li)

                for k in cw['wiki_links']:
                    if k in str_li:
                        str_li  = str_li.replace(k, cw['wiki_links'][k]['entity id'])
                        
                str_li = re.sub(r'<.+?>', '', str_li)
                str_li = re.sub(r'\[[0-9]+\]', ' ', str_li) #remove the numbers in square brackets (wikidata references)
                to_parse.append(str_li)
            to_parse_txt = ' '.join(to_parse)
            cw['to_parse'] = to_parse
            cw['to_parse_txt'] = to_parse_txt

        return self.entities
    








class RelationExtractor(object):
    token = os.getenv('GOOGLEBARD_TOKEN')

    def __init__(self, entties_dict):
        self.entities = entties_dict
    
    def get_relations_bard(self):
        bard = Bard(token=self.token)
        for cw in self.entities:
            bard_res = bard.get_answer("You are an expert in relation extraction from plain text and your aim is to identify the existing relations between the creative work '1984', which is the implicit subject of the text you will be fed with, and other ENTITIES that you will find in the text. ### Return the relationships between '"+cw+"' and the entities marked as 'Entity- ' in the text in the following format: subject | relation | "+cw+" as a pandas dataframe following this example: ```df = pd.DataFrame({'Entity': ['Entity-', 'Entity-', 'Entity-'], 'Relation': ['based on', 'derived from', 'inspired by'], '1984': '1984' })```. ### Text: "+cw['to_parse_txt'])
            out_list = bard_res['content'].replace('\n\n', ' ').replace('\n', ' ').replace('    ', ' ').replace('   ', ' ').replace('  ', ' ').split('```')

            for el in out_list:
                if 'df = pd.DataFrame' in el:
                    df_idx = out_list.index(el)

            df_string = re.sub(r'(python)\s?import pandas as pd (.+)\s?\=', '', out_list[df_idx])
            df_string = re.sub(r'print\(.+\)', '', df_string).strip()

            cw['entity-relations'] = eval(df_string).to_dict()
        return self.entities


    def group_entities(self):
        for cw in self.entities:
            groups = {}
            count = 0
            for sent in cw['to_parse']:
                g = re.findall(r'Entity-[0-9]+', sent)
                if g:
                    groups[count] = g
                count += 1
            cw['entity-groups'] = groups
        return self.entities
    

    def assign_missing_relations(self):
        for cw in self.entities:
            entity_relation = {}
            df = pd.Dataframe(cw['entity-relation'])

            for ent in df.values:
                relation = df[df['Entity'] == ent]['Relation'].values[0]
                entity_relation[ent] = relation
                for group in cw['entity-groups']:
                    if ent in cw['entity-groups'][group]:
                        for e in cw['entity-groups'][group]:
                            if e not in df['Entity'].values:
                                entity_relation[e] = relation
            cw['entity-relation'] = entity_relation
        return self.entities
    

    def disambiguate_relations(self):
        lemma_synset = [('base', 'establish.v.08', 'based on'), ('inspire', 'inspire.v.02', 'inspired by'), ('influence', 'determine.v.02', 'influenced by'), ('derive', 'derive.v.04', 'derived from'), ('adapt', 'adapt.v.01', 'adapted from'), ('reference', 'reference.v.01', 'references'), ('allude', 'allude.v.01', 'alludes to'), ('mention', 'mention.v.01', 'mentions'), ('quote', 'quote.v.01', 'quotes')]
        for cw in self.entities:
            for ent in cw['entity-relation']:
                #if not re.match(r'based\son|(inspired|influenced)(\sby)?|(derive[sd]|adapted)(\sfrom)?|(reference|mention)(s|ed\s(by|in)?)?|alludes?\sto', entity_relation[ent]):
                if re.match(r'based\son', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'based on'
                elif re.match('inspired\sby', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'inspired by'
                elif re.match('influenced\sby', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'influenced by'
                elif re.match('derive[ds](\sfrom)?',cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'derived from'
                elif re.match('adapted(\sfrom)?', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'adapted from'
                elif re.match('reference(s|d)?\s?(by|in)?', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'references'
                elif re.match('mention(s|ed\s(by|in)?)?', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'mentions'
                elif re.match('alludes?(\sto)?', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'alludes to'
                elif re.match('quotes?(\sto)?', cw['entity-relation'][ent]):
                    cw['entity-relation'][ent] = 'quotes'
                else:
                    pos = nlp(cw['entity-relation'][ent])
                    for tok in pos:
                        if tok.pos_ == 'VERB':
                            lemma = tok.lemma_
                            best_syn = ['general', 0]
                            for syn_a in lemma_synset:
                                for syn_b in wn.synsets(lemma, pos=wn.VERB):
                                    similarity = wn.lch_similarity(wn.synset(syn_a[1]), wn.synset(syn_b.name()))
                                    if similarity >= 2.5 and similarity >= best_syn[1]:
                                        best_syn = [syn_a[2], similarity]
                            cw['entity-relation'][ent] = best_syn[0]
                        else:
                            cw['entity-relation'][ent] = 'general influence'

            if cw['fast-check'][ent][1] == 'Artist' or cw['fast-check'][ent][1] == 'Group': #Here we say that if the entity is an artist or a group, we can assume that the relation is 'general influence' rather than 'based on' or 'alludes to' or 'mentions' or 'references
                if cw['entity-relation'][ent] == 'based on' or cw['entity-relation'][ent] == 'references' or cw['entity-relation'][ent] == 'mentions' or cw['entity-relation'][ent] == 'alludes to' or cw['entity-relation'][ent] == 'derived from':
                    cw['entity-relation'][ent] = 'general influence'
        
        return self.entities

