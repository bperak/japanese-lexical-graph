"""
Helper module for Wikidata integration.
Provides functions for querying Wikidata and processing results.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import logging

# Set up logging
logger = logging.getLogger(__name__)

def build_wikidata_query(term, lang='ja'):
    """
    Build a SPARQL query for Wikidata.
    
    Args:
        term (str): The term to search for.
        lang (str): The language code for the term.
        
    Returns:
        str: The SPARQL query.
    """
    query = f"""
    SELECT ?item ?itemLabel ?definition
           ?instanceOf ?instanceOfLabel
           ?subclassOf ?subclassOfLabel
           ?hasPart ?hasPartLabel
           ?partOf ?partOfLabel
           ?officialWebsite
           ?image
           ?synonym ?pronunciation ?usage ?etymology
    WHERE {{
      ?item rdfs:label "{term}"@{lang}.
      
      OPTIONAL {{
        ?item schema:description ?definition .
        FILTER(LANG(?definition) = "en")
      }}
      
      OPTIONAL {{ ?item wdt:P31 ?instanceOf. }}
      OPTIONAL {{ ?item wdt:P279 ?subclassOf. }}
      OPTIONAL {{ ?item wdt:P527 ?hasPart. }}
      OPTIONAL {{ ?item wdt:P361 ?partOf. }}
      OPTIONAL {{ ?item wdt:P856 ?officialWebsite. }}
      OPTIONAL {{ ?item wdt:P18 ?image. }}
      
      # Additional linguistic properties
      OPTIONAL {{ ?item wdt:P5973 ?synonym. }}  # Synonym
      OPTIONAL {{ ?item wdt:P898 ?pronunciation. }}  # IPA pronunciation
      OPTIONAL {{ ?item wdt:P5831 ?usage. }}  # Usage example
      OPTIONAL {{ ?item wdt:P5191 ?etymology. }}  # Etymology
      
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,hr,ja". }}
    }}
    LIMIT 20
    """
    return query

def process_wikidata_results(results, is_fallback=False):
    """
    Process results from Wikidata query.
    
    Args:
        results (dict): The results from the SPARQL query.
        is_fallback (bool): Flag indicating if this is an English fallback search.
        
    Returns:
        dict: Processed results grouped by entity.
    """
    # Group results by entity
    data = {}

    for result in results["results"]["bindings"]:
        item = result["item"]["value"]
        if item not in data:
            data[item] = {
                "Naziv": result.get("itemLabel", {}).get("value", ""),
                "Definicija": result.get("definition", {}).get("value", "No definition available"),
                "Instance of": set(),
                "Subclass of": set(),
                "Has part": set(),
                "Part of": set(),
                "Official Website": set(),
                "Slika": result.get("image", {}).get("value", None),
                "Synonyms": set(),
                "Pronunciation": set(),
                "Usage": set(),
                "Etymology": set(),
                "is_english_fallback": is_fallback  # Add flag for English fallback
            }
        
        # Add instance of
        if "instanceOfLabel" in result:
            data[item]["Instance of"].add(result["instanceOfLabel"]["value"])
        
        # Add subclass of
        if "subclassOfLabel" in result:
            data[item]["Subclass of"].add(result["subclassOfLabel"]["value"])
        
        # Add has part
        if "hasPartLabel" in result:
            data[item]["Has part"].add(result["hasPartLabel"]["value"])
        
        # Add part of
        if "partOfLabel" in result:
            data[item]["Part of"].add(result["partOfLabel"]["value"])
        
        # Add official website
        if "officialWebsite" in result:
            data[item]["Official Website"].add(result["officialWebsite"]["value"])
        
        # Add linguistic properties
        if "synonym" in result:
            data[item]["Synonyms"].add(result["synonym"]["value"])
        
        if "pronunciation" in result:
            data[item]["Pronunciation"].add(result["pronunciation"]["value"])
        
        if "usage" in result:
            data[item]["Usage"].add(result["usage"]["value"])
        
        if "etymology" in result:
            data[item]["Etymology"].add(result["etymology"]["value"])
    
    # Convert sets to lists for JSON serialization
    for item_data in data.values():
        for key, value in item_data.items():
            if isinstance(value, set):
                item_data[key] = list(value)
    
    return data

def get_wikidata_info(term, lang='ja'):
    """
    Get information about a term from Wikidata.
    
    Args:
        term (str): The term to search for.
        lang (str): The language code for the term.
        
    Returns:
        dict: Information about the term.
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.addCustomHttpHeader("User-Agent", "Japanese Lexical Graph Application/1.0")
    query = build_wikidata_query(term, lang)
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        processed_data = process_wikidata_results(results)
        
        # If no results found with Japanese term and we're not already using English,
        # try to get the English translation from the graph and search with that
        if not processed_data and lang == 'ja':
            from app import get_graph
            try:
                # Get the graph from app
                G = get_graph()
                
                # Look for the term in the graph to get its English translation
                for node, data in G.nodes(data=True):
                    if str(node) == term or data.get('japanese') == term:
                        # Get English translations
                        english_translations = data.get('english', [])
                        if english_translations:
                            if isinstance(english_translations, list):
                                # Try the first English translation
                                first_translation = english_translations[0]
                                logger.info(f"No results for '{term}', trying English fallback: '{first_translation}'")
                                
                                # Retry with English term and 'en' language
                                query = build_wikidata_query(first_translation, 'en')
                                sparql.setQuery(query)
                                results = sparql.query().convert()
                                processed_data = process_wikidata_results(results, True)
                                
                                if processed_data:
                                    logger.info(f"Found Wikidata results using English fallback: '{first_translation}'")
                                    return processed_data
                            elif isinstance(english_translations, str):
                                # If english_translations is a string (not a list)
                                logger.info(f"No results for '{term}', trying English fallback: '{english_translations}'")
                                
                                # Retry with English term and 'en' language
                                query = build_wikidata_query(english_translations, 'en')
                                sparql.setQuery(query)
                                results = sparql.query().convert()
                                processed_data = process_wikidata_results(results, True)
                                
                                if processed_data:
                                    logger.info(f"Found Wikidata results using English fallback: '{english_translations}'")
                                    return processed_data
                        break
            except Exception as e:
                logger.error(f"Error during English fallback search: {e}")
                # Continue with original results even if fallback fails
                
        return processed_data
    except Exception as e:
        logger.error(f"Error querying Wikidata: {e}")
        raise 