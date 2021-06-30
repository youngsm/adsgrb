import requests
from .config import read_apikey
from .ECHO import SynchronizedEcho
import concurrent.futures, warnings
from ads import SearchQuery
import time


def getArticles(finds, threading=True, debug=False):
    """
    User function to create a single string containing seperated text bodies from a
    list of `ads.search.Article`'s.

    :param papers:
        A list of ADS articles to download.
    :type papers:
        :class:`list` of `ads.search.Article`
    :param threading:
        Boolean to specify the use of concurrency.
    :type threading:
        :class:`bool`
    :returns:
        String containing each GCN separated by a line.
    """
    papers = finds["articlelist"]
    GRB = finds["GRB"]
    if len(papers) == 0:
        return r"No articles found! ¯\(°_o)/¯"

    articlelist = []
    if threading:
        threads = min(30, len(papers))
        _wrapped_getArticle = lambda article: getArticle(articlelist, article, GRB, debug=debug)

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            executor.map(_wrapped_getArticle, papers)
            executor.shutdown()
    else:
        articlelist = [getArticle(articlelist, paper, GRB, debug=debug) for paper in papers]

    if "gcn" in papers[0].bibcode.lower():
        result = "\n=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=\n\n".join(articlelist)
    else:
        result = articlelist

    ECHO(f"[{GRB}] {len(result)}/{len(papers)} saved.")
    return result


def prepareGRB(GRB):
    if GRB[-1].isalpha():
        finalchar = GRB[-1]
        allbutfinal = GRB[:-1]
    else:
        finalchar = None
        allbutfinal = GRB

    if len(allbutfinal) < 6:
        finalGRB = "0" * (6 - len(allbutfinal)) + allbutfinal
        if finalchar:
            finalGRB += finalchar
    else:
        finalGRB = GRB

    return finalGRB


def getGRBComboQuery(GRB):
    """
    Get the several versions of a GRB name that could come up in ADS searches.
    E.g., 010222A, 10222A, GRB010222A, GRB1022A

    :param GRB:
        The GRB to get name combinations of.
    :type GRB:
        :class:`str`
    :returns:
        String of GRB name combinations separated by "OR" for search in ADS.
    """

    return " OR ".join([f"{GRB}", f"GRB{GRB}"])


def additionalKeywords(keywords):
    """
    Convert keyword(s) to a string to use in an ADS query.

    :param keywords:
        Keywords to specifically search for in addition to the GRB.
    :type keywords:
        :class:`list`,`tuple`,`str`
    :returns:
        String of keyword(s) separated by an "AND" for use in an ADS query.
    """

    if not isinstance(keywords, (type(None), list, tuple)):
        keywords = (keywords,)

    if keywords:
        keywordquery = " AND ".join(keywords)
        query = f"full:({keywordquery})"
    else:
        query = ""

    return query


def gcnSearch(GRB, keywords=None, printlength=True, debug=False):
    """
    User function to find GCNs containing the inputted GRB and optional
    keywords

    :param GRB:
        GRB name; e.g., '010222' or '200205A'
    :type GRB:
        :class:`str`
    :param keywords:
        Keywords to specifically search for in addition to the GRB.
    :type keywords:
        :class:`list`,`tuple`,`str`
    :param printlength:
        Determines whether the user would like the number of articles found to be printed.
    :type printlength:
        :class:`bool`
    :returns:
        A list of `ads.search.Article`'s containing GCNs pertaining to GRB and optional
        keywords.
    """

    if keywords is not None:
        warnings.warn("Keywords aren't working correctly right now.", stacklevel=2)
    assert isinstance(GRB, str), "GRB is not of type string."
    query = f"bibstem:GCN {getGRBComboQuery(GRB)}"
    keywords = additionalKeywords(keywords)
    finds = list(SearchQuery(q=f"{query + keywords}", fl=["bibcode", "identifier"]))
    if debug:
        ECHO(f"[{GRB}] Query: {query + keywords}")
    if printlength:
        ECHO(f"[{GRB}] {len(finds)} candidates.")
    return finds


def litSearch(GRB, keywords=None, printlength=True, debug=False):
    """
    User function to find literature containing the inputted GRB and optional
    keywords

    :param GRB:
        GRB name; e.g., '010222' or '200205A'
    :type GRB:
        :class:`str`
    :param keywords:
        Keywords to specifically search for in addition to the GRB.
    :type keywords:
        :class:`list`,`tuple`,`str`
    :param printlength:
        Determines whether the user would like the number of articles found to be printed.
    :type printlength:
        :class:`bool`
    :returns:
        A list of `ads.search.Article`'s containing GCNs pertaining to GRB and optional
        keywords.
    """
    assert isinstance(GRB, str), "GRB is not of type string."
    GRB = prepareGRB(GRB)
    query = getGRBComboQuery(GRB)
    keywords = additionalKeywords(keywords)
    fullquery = f"title:{query} OR abstract:{query} OR keyword:{query} {keywords} -bibstem:GCN"
    finds = list(SearchQuery(q=fullquery, fl=["bibcode", "identifier", "title", "author", "year"], rows=100))
    if (printlength or debug) and len(finds) > 0:
        ECHO(f"[{GRB}] {len(finds)} found.")
    if debug:
        ECHO(f"[{GRB}] Query: '{fullquery}'")
        ECHO(f"Finds: {', '.join([find.bibcode for find in finds])}")

    return {"GRB": GRB, "articlelist": finds}


def getArticle(articlelist, article, GRB, debug=False):
    """
    Download an article from arXiv or other sources.
    :param articlelist:
        The string list to append article texts to.
    :type articlelist:
        :class:`list`
    :param article:
        The ADS article to retrieve.
    :type article:
        :class:`ads.search.Article`
    :returns:
        Nothing. Side effect of appending text of article body to articlelist.
    Modified from https://github.com/andycasey/ads/blob/master/examples/monthly-institute-publications/stromlo.py#22
    """

    if debug:
        ECHO(f"[{GRB}] Retrieving {article.bibcode}")
    isGCN = "GCN" in article.bibcode
    header = {"Authorization": f"Bearer {read_apikey()}"}
    # Ask ADS to redirect us to the journal article.
    if isGCN:
        params = {"bibcode": article.bibcode, "link_type": "EJOURNAL"}
    else:
        params = {"bibcode": article.bibcode, "link_type": "ESOURCE"}

    url = requests.get("http://adsabs.harvard.edu/cgi-bin/nph-data_query", params=params).url

    if isGCN:
        q = requests.get(url)
    else:
        url = f"https://api.adsabs.harvard.edu/v1/resolver/{article.bibcode}/esource"
        q = requests.get(
            url,
            headers=header,
            allow_redirects=False,
        )
        if not q.ok:
            if debug:
                ECHO(
                    f"[{GRB}] Pass 1: Error retrieving {article.bibcode} ({q.status_code}): https://ui.adsabs.harvard.edu/abs/{article.bibcode}/abstract."
                )
                q.raise_for_status()
                return
            else:
                return

        deserialized = q.json()
        try:
            records = deserialized["links"]["records"]
            for record in records:
                linktype = record["link_type"]
                link = record["url"]
                if "PDF" in linktype and not "iop" in link and not "doi" in link and not "$" in link:
                    # switch any arxiv url to export.arxiv so we don't get locked out
                    url = link.replace("arxiv.org", "export.arxiv.org")
                    if "arxiv" in url:
                        q = requests.get(url, stream=True)
                        time.sleep(10)
                    q = requests.get(url, stream=True)
                    break
                # record is guaranteed to be of length > 0
                elif record == records[-1]:
                    ECHO(f"[{GRB}] Could not find suitable link for {article.bibcode}. {link}")
                    return
        except:
            # switch any arxiv url to export.arxiv so we don't get locked out
            linktype = deserialized["link_type"]
            url = deserialized["link"].replace("arxiv.org", "export.arxiv.org")
            if "PDF" in linktype and not "iop" in link and not "doi" in link and not "$" in link:
                if "arxiv" in url:
                    q = requests.get(url, stream=True)
                    time.sleep(10)
                q = requests.get(url, stream=True)
            else:
                ECHO(f"[{GRB}] Pass 2: No suitable link for {article.bibcode}. {link}")
                return

    if not q.ok:
        if debug:
            ECHO(f"[{GRB}] Pass 2: Error retrieving {article.bibcode} ({q.status_code}): {url}")
            q.raise_for_status()
            return
        else:
            return

    # Check if the journal has given back forbidden HTML.
    try:
        if q.content.contains("</html>", case=False) or not str(q.content):
            ECHO(f"[{GRB}] Pass 2: Error retrieving {article.bibcode} (200): {url}")
            return
    except:
        if q.text.contains("</html>", case=False) or not str(q.text):
            ECHO(f"[{GRB}] Pass 2: Error retrieving {article.bibcode} (200): {url}")
            return

    if isGCN:
        articlelist.append(q.text)
    else:
        articlelist.append([q.content, article.title, article.year, url])


ECHO = SynchronizedEcho()
