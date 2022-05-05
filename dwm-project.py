import requests
import lxml.html
import rdflib
import sys


#Part one - Create ontology
WIKI_PREFIX = "http://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org"
graph = rdflib.Graph()
countries_dict={}

def first_letter(s):
    m = re.search(r'[a-z]', s, re.I)
    if m is not None:
        return m.start()
    return -1

def get_wiki_url(name):
    name = name.replace(" ", "_")
    return requests.get(WIKI_PREFIX + "/wiki/" + name)

def get_list_of_countries():
    res = requests.get("https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)")
    doc = lxml.html.fromstring(res.content)
    countries = []
    for i in range(2, 235):
        countries.append(doc.xpath("//*[@id='mw-content-text']/div[1]/table/tbody/tr[" + str(i) + "]/td[1]/descendant::a[1]//text()")[0])
    return countries


""" Receives a name of a person and returns the place and date of birth """
def get_personal_info(name):
        res = get_wiki_url(name)
        doc = lxml.html.fromstring(res.content)
        info_box = doc.xpath("//table[contains(@class, 'infobox')]")
        born = info_box[0].xpath("//table//th[contains(text(), 'Born')]")
        dob = born[0].xpath("./../td//span[@class='bday']//text()")[0].replace(" ", "_")
        pob = born[0].xpath("./../td//text()")[-1]
        pob = pob[first_letter(pob):].replace(" ", "_")
        return [fixing_prefix(name),fixing_prefix(pob), fixing_prefix(dob)]


""" Receives a name of a country and add to the dict the relevant info """
def get_country_info(name):
    res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    Government=info_box[0].xpath("//table//th[contains(text(), 'Government')]")
    president_name=Government[0]

    president_name = info_box[0].xpath("//table//th[contains(text(), 'Government')]")
    prime_minister_name =
    population = born[0].xpath("./../td//a/text()")[0].replace(" ", "_")
    area =
    government =
    capital =

    president=get_personal_info(president_name)
    prime_minister=get_personal_info(prime_minister_name)
    countries_dict[name] = [president, prime_minister, population, area, government, capital]

"""fixing for ontology"""
def fixing_prefix(object):
    return rdflib.URIRef(f'{EXAMPLE_PREFIX}{object}')


def triplets_to_ontology(subject,property, object): #subject=country/person ,property
    graph.add((subject, property, object))

"""from  countries dict to triplets for ontology """
def to_triplets(dict):
    country_property = ['president_is','prime_minister_is','population_is','area_is','government_from','capital_is']
    person = ['name','place_of_birth','date_of_birth']
    for country in dict.keys():
        info=dict[country]
        for i in range(6):
            if (i == 0 or i == 1) :
                triplets_to_ontology(info[i][1],fixing_prefix(person[1]),info[i][1])
                triplets_to_ontology(info[i][2],fixing_prefix(person[2]),info[i][2])
                triplets_to_ontology(fixing_prefix(country), fixing_prefix(country_property[i]), info[i][0])
            else:
                triplets_to_ontology(fixing_prefix(country),fixing_prefix(country_property[i]),fixing_prefix(info[i]))


def create ():
    countries_list=get_list_of_countries() #create countries list
    for country in countries_list:
        get_country_info(country) #fill values in countries dictionary
    to_triplets(countries_dict) #create ontology
    graph.serialize("ontology.nt", format="nt")
    sys.exit()

#Part two - question
def question ():

    q=sys.argv[2].replace(" ", "_")
    graph=rdflib.Graph()
    graph.parse("ontology.nt", format="nt")
    sys.exit()



#Main
if (sys.argv[1] == "create"):
    create()
if (sys.argv[1] == "question"):
    question()

