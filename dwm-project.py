import requests
import lxml.html
import rdflib
import sys
import re

# Part one - Create ontology
WIKI_PREFIX = "http://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org/"
MORE_THAN_ONE_CAPITAL = ["Bolivia", "Eswatini", "South Africa", "Malaysia", "Sri Lanka"]
graph = rdflib.Graph()
countries_dict = {}

"""fixing for ontology"""


def fixing_prefix(s):
    res = re.sub('\s+', '_', s)
    return rdflib.URIRef(f'{EXAMPLE_PREFIX}{res}')


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
        countries.append(doc.xpath(
            "//*[@id='mw-content-text']/div[1]/table/tbody/tr[" + str(i) + "]/td[1]/descendant::a[1]//text()")[0])
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
    return [fixing_prefix(name), fixing_prefix(pob), fixing_prefix(dob)]


def get_government_type(info_box):
    gov = info_box[0].xpath("//tbody/tr[./descendant::a[contains(text(), 'Government')]]/td/a/text()")
    res = set()
    for entry in gov:
        res.add(fixing_prefix(entry))
    return res


def get_president(info_box):
    try:
        president = info_box[0].xpath("//tbody/tr[./descendant::a[contains(text(), 'President')]]/td/a/text()")
        res = set()
        for entry in president:
            res.add(fixing_prefix(entry))
        return res
    except:
        return None


def get_pm(info_box):
    try:
        pm = info_box[0].xpath("//tbody/tr[./descendant::a[contains(text(), 'Prime Minister')]]/td/a/text()")
        res = set()
        for entry in pm:
            res.add(fixing_prefix(entry))
        return res
    except:
        return None


def get_population(info_box):
    res = set()
    res.add(fixing_prefix(info_box[0].xpath("//tbody//td[./descendant::a["
                                            "@href='/wiki/List_of_countries_and_dependencies_by_population']]/"
                                            "text()")[0]))
    return res


def get_area(info_box):
    res = set()
    res.add(fixing_prefix(info_box[0].xpath("//tbody//td[./descendant::a"
                                            "[@href='/wiki/List_of_countries_and_dependencies_by_area']]/text()")[0]))
    return res


def get_capital(info_box, country_name):
    try:
        if country_name in MORE_THAN_ONE_CAPITAL:
            capital = info_box[0].xpath("//tbody//tr[./th[contains(text(), 'Capital')]]/td//"
                                        "a[@title != 'Geographic coordinate system']/text()")
        else:
            capital = info_box[0].xpath("//tbody//tr[./th[contains(text(), 'Capital')]]/td/a[1]/text()")
        res = set()
        for entry in capital:
            res.add(fixing_prefix(entry))
        return res
    except:
        return None


""" Receives a name of a country and add to the dict the relevant info """


def get_country_info(name):
    res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    return {
        "Area": get_area(info_box),
        "Government Type": get_government_type(info_box),
        "President": get_president(info_box),
        "Prime Minister": get_pm(info_box),
        "Population": get_population(info_box),
        "Capital": get_capital(info_box, name)
    }


def triplets_to_ontology(subject, property, object):  # subject=country/person ,property
    graph.add((subject, property, object))


"""from  countries dict to triplets for ontology """


def to_triplets(dict):
    country_property = ['president_is', 'prime_minister_is', 'population_is', 'area_is', 'government_from',
                        'capital_is']
    person = ['name', 'place_of_birth', 'date_of_birth']
    for country in dict.keys():
        info = dict[country]
        for i in range(6):
            if i == 0 or i == 1:
                triplets_to_ontology(info[i][1], fixing_prefix(person[1]), info[i][1])
                triplets_to_ontology(info[i][2], fixing_prefix(person[2]), info[i][2])
                triplets_to_ontology(fixing_prefix(country), fixing_prefix(country_property[i]), info[i][0])
            else:
                triplets_to_ontology(fixing_prefix(country), fixing_prefix(country_property[i]), fixing_prefix(info[i]))


def create():
    countries_list = get_list_of_countries()  # create countries list
    for country in countries_list:
        get_country_info(country)  # fill values in countries dictionary
    to_triplets(countries_dict)  # create ontology
    graph.serialize("ontology.nt", format="nt")
    sys.exit()


# Part two - question
def question():
    q = sys.argv[2].replace(" ", "_")
    graph = rdflib.Graph()
    graph.parse("ontology.nt", format="nt")
    sys.exit()


# Main
# if (sys.argv[1] == "create"):
#    create()
# if (sys.argv[1] == "question"):
#    question()
