import requests
import lxml.html
import rdflib
import sys
import re

# Part one - Create ontology
WIKI_PREFIX = "http://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org/"
PROBLEMATIC_CAPITAL = {"Vatican City": "", "Tokelau": "", "Caribbean Netherlands": "Bonaire",
                       "Antigua and Barbuda": "", "Mayotte": "Mamoudzou", "Macao": "", "Palestine": "Ramallah",
                       "Hong Kong": "", "Singapore": "Singapore", "Switzerland": "Bern", "Western Sahara": "Laayoune"}
graph = rdflib.Graph()
countries_dict = {}

"""fixing for ontology"""


def fixing_prefix(s):
    s = s.lstrip()
    res = re.sub('\s+', '_', s)
    return rdflib.URIRef(f'{EXAMPLE_PREFIX}{res}')


def first_letter(s):
    m = re.search(r'[a-z]', s, re.I)
    if m is not None:
        return m.start()
    return -1


def get_wiki_url(name):
    if name == "DR Congo":
        name = "Democratic Republic of the Congo"
    if name == "Palestine":
        name = "State of Palestine"
    if name == "Georgia":
        name = "Georgia (country)"
    if name == "Micronesia":
        name = "Federated States of Micronesia"
    if name == "Ireland":
        name = "Republic of Ireland"
    name = name.replace(" ", "_")
    return requests.get(WIKI_PREFIX + "/wiki/" + name)


def get_list_of_countries():
    res = requests.get("https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)")
    doc = lxml.html.fromstring(res.content)
    countries = []
    for i in range(2, 235):
        name = doc.xpath(
            "//*[@id='mw-content-text']/div[1]/table/tbody/tr[" + str(i) + "]/td[1]/descendant::a[1]//text()")[0]
        if name == "Congo":
            name = "DR Congo"
        countries.append(name)
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
    gov = info_box[0].xpath("//tbody/tr[./descendant::*[contains(text(), 'Government')]]/td/a/text()")
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


def get_population(info_box, name):
    res = set()
    try:
        population = info_box[0].xpath("//tbody/tr[.//text() = 'Population']/td//text()")[0]
    except IndexError:
        population = info_box[0].xpath("//tbody/tr[.//text() = 'Population']/following::tr[1]/td//text()")[0]
    population = population.lstrip()
    population = population.split(" ")[0] if " " in population else population
    population = population.replace('(', '').replace(')', '').replace("'", '')
    res.add(fixing_prefix(population))
    return res


def get_area(info_box, name):
    res = set()
    try:
        area_raw = info_box[0].xpath("//tbody//tr[.//text()[contains(., 'Area')]]//td/text()")[0]
    except IndexError:
        area_raw = info_box[0].xpath("//tbody//tr[.//text()[contains(., 'Area')]]/following::tr[1]//td/text()")[0]
    area_final = ""
    if "mi" in area_raw:
        flag = False
        for word in area_raw.split():
            if flag:
                if word == "km":
                    area_final += " "
                area_final += word
            if word == "mi":
                flag = True
    else:
        area_final = area_raw
    area_final = area_final.replace('(', '').replace(')', '').replace("'", '')
    if "km" not in area_final:
        area_final += " km"
    res.add(fixing_prefix(area_final))
    return res


def get_capital(info_box, country_name):
    if country_name in PROBLEMATIC_CAPITAL:
        capital = PROBLEMATIC_CAPITAL[country_name]
    else:
        try:
            capital = info_box[0].xpath("//tbody//tr[./th[contains(text(), 'Capital')]]/td//a[1]/text()")[0]
        except IndexError:
            capital = info_box[0].xpath("//tbody//tr[./th/a[contains(text(), 'Prefecture')]]/td//a[1]/text()")[0]
    res = set()
    res.add(fixing_prefix(capital))
    print(capital)
    return res


""" Receives a name of a country and add to the dict the relevant info """


def get_country_info(name):
    res = get_wiki_url(name)
    doc = lxml.html.fromstring(res.content)
    info_box = doc.xpath("//table[contains(@class, 'infobox')]")
    return {
        "Area": get_area(info_box, name),
        "Government Type": get_government_type(info_box),
        "President": get_president(info_box),
        "Prime Minister": get_pm(info_box),
        "Population": get_population(info_box, name),
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


for country in get_list_of_countries():
    get_country_info(country)

# Main
# if (sys.argv[1] == "create"):
#    create()
# if (sys.argv[1] == "question"):
#    question()
