import unittest
from rdflib import *

# Load the knowledge graph
mucho_gustore = Graph()
mucho_gustore.parse("./knowledge_graphs/kg_1C2QJNTmsTxCDBuIgai8QV.ttl", format="turtle")

# Define the test class
class TestCompetencyQuestions(unittest.TestCase):

    # Test CQ1: Who are the artists responsible for the creation of a particular song?
    def test_CQ1(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                SELECT ?artist ?artistLabel
                WHERE {
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:hasAuthor ?artist .
                    ?artist rdfs:label ?artistLabel .
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.artist, row.artistLabel))
        self.assertEqual(result, [(URIRef('https://www.wikidata.org/wiki/Q22151'), Literal('Muse', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])


    # Test CQ2: Which are the music genres related to some specific artists?
    def test_CQ2(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
                SELECT ?genre ?genreLabel
                WHERE {
                    <https://www.wikidata.org/wiki/Q22151> mm:hasGenre ?genre .
                    ?genre rdfs:label ?genreLabel .
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.genre, row.genreLabel))
        self.assertEqual(result, [(URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#modern_rock'), Literal('modern_rock', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#permanent_wave'), Literal('permanent_wave', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#rock'), Literal('rock', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])


    # Test CQ3: Which creative works are referenced within the lyrics of a particular song?
    def test_CQ3(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>

                SELECT ?cw ?title
                WHERE {
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:references ?cw .
                    ?cw core:title ?title .
                }
            """
        
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.cw, row.title))
        self.assertEqual(result, [(URIRef('https://www.wikidata.org/wiki/Q208460'), Literal('1984', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])


    # Test CQ4: Which annotations of a particular song do contain a reference to a particular creative work?
    def test_CQ4(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>

                SELECT ?annotation
                WHERE {
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:qualifiedReference ?reference .
                    ?reference prov:entity <https://www.wikidata.org/wiki/Q208460> ;
                                mucho:hasInformationSource ?annotation .
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append(row.annotation)
        self.assertEqual(result, [URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_0'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_1'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_2'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_3'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_4'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_7'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_8'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_9')])


    # Test CQ5: What is the text of the annotations referencing a particular creative work? (take one single annotation for the test knowing the result of the previous query)
    def test_CQ5(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>

                SELECT ?text
                WHERE {
                    <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_0> core:text ?text .
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append(row.text)
        self.assertEqual(result, [Literal('He wants from the significant other not to let him go. Lips being sealed can be interpreted in two ways: one, they should be always ‘that’ close and two, they should never utter a word to anybody about each other. In 1984, they have to ‘keep their lips sealed’ i.e. keep their romance a secret, as love is considered a crime in the novel’s world. If the government found out about them, they would be punished, as specified in the verses.', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))])
        

    # Test CQ6: Which lyrics fragments are related to the annotations referencing a particular creative work?
    def test_CQ6(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>

                SELECT ?lyricsFragment ?annotation
                WHERE {
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:qualifiedReference ?reference .
                    ?reference prov:entity <https://www.wikidata.org/wiki/Q208460> ;
                                mucho:hasInformationSource ?annotation .
                    ?lyricsFragment mucho:hasAnnotation ?annotation .
                    
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.lyricsFragment, row.annotation))
        self.assertEqual(result, [(URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_0'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_0')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_1'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_1')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_2'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_2')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_3'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_3')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_4'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_4')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_7'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_7')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_8'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_8')), (URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#fragment_9'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#annotation_9'))])


    # Test CQ7: Which are the entities related to the creative works referenced by a specific song (and therefore to the song itself with a two-step connection)?
    def test_CQ7(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>

                SELECT ?entity ?entityLabel
                WHERE {
                    VALUES ?relation { prov:wasInfluencedBy prov:wasDerivedFrom mucho:isAdaptationOf mucho:isBasedOn mucho:references mucho:alludesTo mucho:cites mucho:mentions mucho:wasInspiredBy } 
                    
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:references ?middleEntity .
                    ?entity ?relation ?middleEntity .
                    ?entity rdfs:label ?entityLabel .  
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.entity, row.entityLabel))
        self.assertEqual(result, [(URIRef('http://dbpedia.org/resource/2_+_2_=_5_(song)'), Literal('2 + 2 = 5 (song)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Chain_of_Command_(Star_Trek:_The_Next_Generation)'), Literal('Chain of Command (Star Trek: The Next Generation)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Diamond_Dogs'), Literal('Diamond Dogs', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Hail_to_the_Thief'), Literal('Hail to the Thief', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Muse_(band)'), Literal('Muse (band)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Radiohead'), Literal('Radiohead', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Star_Trek:_The_Next_Generation'), Literal('Star Trek: The Next Generation', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_Resistance_(album)'), Literal('The Resistance (album)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Hugh_Hopper'), Literal('Hugh Hopper', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Soft_Machine'), Literal('Soft Machine', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Eric_Sykes'), Literal('Eric Sykes', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Spirit_(band)'), Literal('Spirit (band)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_Goon_Show'), Literal('The Goon Show', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/1984_(advertisement)'), Literal('1984 (advertisement)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Paul_Weller'), Literal('Paul Weller', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_Jam'), Literal('The Jam', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/This_Is_the_Modern_World'), Literal('This Is the Modern World', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4'), Literal('Resistance', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Doctor_Who'), Literal('Doctor Who', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Oranges_and_Lemons'), Literal('Oranges and Lemons', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_God_Complex'), Literal('The God Complex', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])


    # Test CQ8: Which of the entities related to the creative works referenced by a specific song are creative works?
    def test_CQ8(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>
                PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>

                SELECT ?entity ?entityLabel
                WHERE {
                    VALUES ?entityType { core:InformationObject mm:MusicEntity mucho:MusicAlbum mucho:Song mucho:AudiovisualEntity mucho:LiteraryEntity mucho:VisualArtEntity }
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:references ?middleEntity .
                    ?entity ?relation ?middleEntity ;
                            a ?entityType ;
                            rdfs:label ?entityLabel .  
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.entity, row.entityLabel))
        self.assertEqual(result, [(URIRef('http://dbpedia.org/resource/Diamond_Dogs'), Literal('Diamond Dogs', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Hail_to_the_Thief'), Literal('Hail to the Thief', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_Resistance_(album)'), Literal('The Resistance (album)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/This_Is_the_Modern_World'), Literal('This Is the Modern World', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/2_+_2_=_5_(song)'), Literal('2 + 2 = 5 (song)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Oranges_and_Lemons'), Literal('Oranges and Lemons', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4'), Literal('Resistance', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/1984_(advertisement)'), Literal('1984 (advertisement)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Chain_of_Command_(Star_Trek:_The_Next_Generation)'), Literal('Chain of Command (Star Trek: The Next Generation)', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Doctor_Who'), Literal('Doctor Who', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/Star_Trek:_The_Next_Generation'), Literal('Star Trek: The Next Generation', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_God_Complex'), Literal('The God Complex', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string'))), (URIRef('http://dbpedia.org/resource/The_Goon_Show'), Literal('The Goon Show', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])


    # Test CQ9: By what kind of relation are the creative works referenced by a specific song connected with their related entities?
    def test_CQ9(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>
                PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>

                SELECT ?entity ?relation
                WHERE {
                    VALUES ?entityType { core:InformationObject mm:MusicEntity mucho:MusicAlbum mucho:Song mucho:AudiovisualEntity mucho:LiteraryEntity mucho:VisualArtEntity }
                    <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:references ?middleEntity .
                    ?entity ?relation ?middleEntity ;
                            a ?entityType .  
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.entity, row.relation))
        self.assertEqual(result, [(URIRef('http://dbpedia.org/resource/Diamond_Dogs'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/Hail_to_the_Thief'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/The_Resistance_(album)'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/This_Is_the_Modern_World'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#references')), (URIRef('http://dbpedia.org/resource/2_+_2_=_5_(song)'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/Oranges_and_Lemons'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#cites')), (URIRef('https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#references')), (URIRef('http://dbpedia.org/resource/1984_(advertisement)'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#references')), (URIRef('http://dbpedia.org/resource/Chain_of_Command_(Star_Trek:_The_Next_Generation)'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/Doctor_Who'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#cites')), (URIRef('http://dbpedia.org/resource/Star_Trek:_The_Next_Generation'), URIRef('http://www.w3.org/ns/prov#wasInfluencedBy')), (URIRef('http://dbpedia.org/resource/The_God_Complex'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#cites')), (URIRef('http://dbpedia.org/resource/The_Goon_Show'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#isBasedOn'))])


    # Test CQ10: Which is the web resource from where the relations between a particular creative work and its connected entities were extracted?
    def test_CQ10(self):
        q = """
            PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
            PREFIX core: <https://w3id.org/polifonia/ontology/core/>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
            PREFIX core: <https://w3id.org/polifonia/ontology/core/>

            SELECT DISTINCT ?entity ?relation ?infoSource
            WHERE {
                VALUES ?entityType { core:InformationObject mm:MusicEntity mucho:MusicAlbum mucho:Song mucho:AudiovisualEntity mucho:LiteraryEntity mucho:VisualArtEntity }
                <https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4> mucho:references ?middleEntity .
                ?entity ?relation ?qRelation .
                ?qRelation prov:entity ?middleEntity ;
                            mucho:influenceInformationSource ?infoSource.
            }
        """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.entity, row.relation, row.infoSource))
        self.assertEqual(result, [(URIRef('http://dbpedia.org/resource/1984_(advertisement)'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedReference'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/2_+_2_=_5_(song)'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Chain_of_Command_(Star_Trek:_The_Next_Generation)'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Diamond_Dogs'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Doctor_Who'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedCitation'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Eric_Sykes'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedBasis'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Hail_to_the_Thief'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Hugh_Hopper'), URIRef('http://www.w3.org/ns/prov#qualifiedDerivation'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Muse_(band)'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Oranges_and_Lemons'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedCitation'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Paul_Weller'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedReference'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Radiohead'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Soft_Machine'), URIRef('http://www.w3.org/ns/prov#qualifiedDerivation'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Spirit_(band)'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedBasis'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/Star_Trek:_The_Next_Generation'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/The_God_Complex'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedCitation'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/The_Goon_Show'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedBasis'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/The_Jam'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedReference'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/The_Resistance_(album)'), URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('http://dbpedia.org/resource/This_Is_the_Modern_World'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedReference'), Literal('https://en.wikipedia.org/wiki/Nineteen_Eighty-Four', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI'))), (URIRef('https://musicbrainz.org/recording/09595161-717b-4ec5-94d1-9040aab8aae4'), URIRef('https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#qualifiedReference'), Literal('https://genius.com/Muse-resistance-lyrics', datatype=URIRef('http://www.w3.org/2001/XMLSchema#anyURI')))])


    # Test CQ11: What is the source text including the relations to be extracted? (take one for the test knowing the result of the previous query)
    def test_CQ11(self):
        q = """
                PREFIX mucho: <https://raw.githubusercontent.com/tommasobattisti/MuCH-O/main/ontology/mucho.owl#>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>
                PREFIX prov: <http://www.w3.org/ns/prov#>
                PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
                PREFIX core: <https://w3id.org/polifonia/ontology/core/>

                SELECT DISTINCT ?entity ?relation ?sourceText
                WHERE {
                    VALUES ?relation { prov:qualifiedInfluence prov:qualifiedDerivation mucho:qualifiedAdaptation mucho:qualifiedBasis mucho:qualifiedReference mucho:qualifiedAllusion mucho:qualifiedCitation mucho:qualifiedMention mucho:qualifiedInspiration } 
                    VALUES ?entityType { core:InformationObject mm:MusicEntity mucho:MusicAlbum mucho:Song mucho:AudiovisualEntity mucho:LiteraryEntity mucho:VisualArtEntity }
                    
                    <http://dbpedia.org/resource/Diamond_Dogs> ?relation ?qRelation .
                    ?qRelation prov:entity ?middleEntity ;
                                mucho:influenceSourceText ?sourceText .
                }
            """
        res = mucho_gustore.query(q)
        result = []
        for row in res:
            result.append((row.entity, row.relation, row.sourceText))
        self.assertEqual(result, [(None, URIRef('http://www.w3.org/ns/prov#qualifiedInfluence'), Literal('In 1974, David Bowie released the album Diamond Dogs, which is thought to be loosely based on the novel Nineteen Eighty-Four. It includes the tracks "We Are The Dead", "1984" and "Big Brother". Before the album was made, Bowie\'s management (MainMan) had planned for Bowie and Tony Ingrassia (MainMan\'s creative consultant) to co-write and direct a musical production of Orwell\'s Nineteen Eighty-Four, but Orwell\'s widow refused to give MainMan the rights. ', datatype=URIRef('http://www.w3.org/2001/XMLSchema#string')))])




if __name__ == '__main__':
    unittest.main()