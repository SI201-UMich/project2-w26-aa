# SI 201 HW4 (Library Checkout System)
# Your name: Analu Jahi, Antonio Said
# Your student id: 41395396, 78519368
# Your email: analuj@umich.edu, awsaid@umich.edu
# Who or what you worked with on this homework (including generative AI like ChatGPT):
# If you worked with generative AI also add a statement for how you used it.
# e.g.:
# Asked ChatGPT for hints on debugging and for suggestions on overall code structure
#
# Did your use of GenAI on this assignment align with your goals and guidelines in your Gen AI contract? If not, why?
#
# --- ARGUMENTS & EXPECTED RETURN VALUES PROVIDED --- #
# --- SEE INSTRUCTIONS FOR FULL DETAILS ON METHOD IMPLEMENTATION --- #

from bs4 import BeautifulSoup
import re
import os
import csv
import unittest
import requests  # kept for extra credit parity


# IMPORTANT NOTE:
"""
If you are getting "encoding errors" while trying to open, read, or write from a file, add the following argument to any of your open() functions:
    encoding="utf-8-sig"
"""

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def load_listing_results(html_path) -> list[tuple]:
    """
    Load file data from html_path and parse through it to find listing titles and listing ids.

    Args:
        html_path (str): The path to the HTML file containing the search results

    Returns:
        list[tuple]: A list of tuples containing (listing_title, listing_id)
    """
    with open(html_path, encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f, "html.parser")

    results = []
    seen_ids = set()

    links = soup.find_all("a", href=re.compile(r"/rooms(?:/plus)?/\d+"))
    for a in links:
        href = a.get("href", "")
        m = re.search(r"/rooms(?:/plus)?/([0-9]+)", href)
        if not m:
            continue
        listing_id = m.group(1)
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        # Walk up the DOM to find a parent element that contains the listing title
        parent = a.parent
        title = None
        for _ in range(12):
            text = parent.get_text(separator="|").strip()
            parts = [p.strip() for p in text.split("|") if p.strip()]
            if parts and len(parts[0]) > 3:
                title = parts[0]
                break
            parent = parent.parent
            if parent is None:
                break

        if title is not None:
            results.append((title, listing_id))

    return results


def get_listing_details(listing_id) -> dict:
    """
    Parse through listing_<id>.html to extract listing details.

    Args:
        listing_id (str): The listing id of the Airbnb listing

    Returns:
        dict: Nested dictionary in the format:
        {
            "<listing_id>": {
                "policy_number": str,
                "host_type": str,
                "host_name": str,
                "room_type": str,
                "location_rating": float
            }
        }
    """
    html_path = os.path.join(BASE_DIR, "html_files", f"listing_{listing_id}.html")
    with open(html_path, encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f, "html.parser")

    # --- Policy number ---
    policy_number = None
    for li in soup.find_all("li"):
        txt = li.get_text()
        if "Policy number" in txt or "policy number" in txt:
            span = li.find("span")
            if span:
                raw = span.get_text().strip()
            else:
                raw = re.sub(r"[Pp]olicy number:?\s*", "", txt).strip()
            # Strip BOM and extra whitespace
            raw = raw.replace("\ufeff", "").strip()
            # Categorize
            if raw.lower() == "pending":
                policy_number = "Pending"
            elif raw.lower() == "exempt":
                policy_number = "Exempt"
            else:
                policy_number = raw
            break
    if policy_number is None:
        policy_number = "Exempt"

    # --- Host type ---
    host_type = "regular"
    for span in soup.find_all("span"):
        if span.get_text().strip() == "Superhost":
            host_type = "Superhost"
            break

    # --- Host name and room type ---
    # The h2 element that contains "hosted by" has the subtitle and host name
    host_name = ""
    room_type = "Entire Room"
    for h2 in soup.find_all("h2"):
        txt = h2.get_text()
        if "hosted by" in txt.lower():
            # Extract name after "hosted by"
            name_raw = re.sub(r".*hosted by\s*", "", txt, flags=re.IGNORECASE).strip()
            # Normalize non-breaking spaces
            host_name = name_raw.replace("\xa0", " ").strip()
            # Determine room type from the subtitle
            if "Private" in txt:
                room_type = "Private Room"
            elif "Shared" in txt:
                room_type = "Shared Room"
            else:
                room_type = "Entire Room"
            break

    # --- Location rating ---
    location_rating = 0.0
    for div in soup.find_all("div", class_="_y1ba89"):
        if div.get_text().strip() == "Location":
            parent = div.parent
            rating_span = parent.find("span", {"aria-hidden": "true"})
            if rating_span:
                try:
                    location_rating = float(rating_span.get_text().strip())
                except ValueError:
                    pass
            break

    return {
        listing_id: {
            "policy_number": policy_number,
            "host_type": host_type,
            "host_name": host_name,
            "room_type": room_type,
            "location_rating": location_rating,
        }
    }


def create_listing_database(html_path) -> list[tuple]:
    """
    Use prior functions to gather all necessary information and create a database of listings.

    Args:
        html_path (str): The path to the HTML file containing the search results

    Returns:
        list[tuple]: A list of tuples. Each tuple contains:
        (listing_title, listing_id, policy_number, host_type, host_name, room_type, location_rating)
    """
    listings = load_listing_results(html_path)
    database = []

    for listing_title, listing_id in listings:
        details = get_listing_details(listing_id)
        inner = details[listing_id]
        database.append((
            listing_title,
            listing_id,
            inner["policy_number"],
            inner["host_type"],
            inner["host_name"],
            inner["room_type"],
            inner["location_rating"],
        ))

    return database


def output_csv(data, filename) -> None:
    """
    Write data to a CSV file with the provided filename.

    Sort by Location Rating (descending).

    Args:
        data (list[tuple]): A list of tuples containing listing information
        filename (str): The name of the CSV file to be created and saved to

    Returns:
        None
    """
    sorted_data = sorted(data, key=lambda row: row[6], reverse=True)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Listing Title",
            "Listing ID",
            "Policy Number",
            "Host Type",
            "Host Name",
            "Room Type",
            "Location Rating",
        ])
        for row in sorted_data:
            writer.writerow(row)


def avg_location_rating_by_room_type(data) -> dict:
    """
    Calculate the average location_rating for each room_type.

    Excludes rows where location_rating == 0.0 (meaning the rating
    could not be found in the HTML).

    Args:
        data (list[tuple]): The list returned by create_listing_database()

    Returns:
        dict: {room_type: average_location_rating}
    """
    # TODO: Implement checkout logic following the instructions
    # ==============================
    # YOUR CODE STARTS HERE
    # ==============================

    totals = {}
    counts = {}
    for row in data:
        room_type = row[5]
        location_rating = row[6]
        if location_rating == 0.0:
            continue

        totals[room_type] = totals.get(room_type, 0.0) + location_rating
        counts[room_type] = counts.get(room_type, 0) + 1

    averages = {}
    for room_type in totals:
        averages[room_type] = round(totals[room_type] / counts[room_type], 10)


    return averages

    # ==============================
    # YOUR CODE ENDS HERE
    # ==============================


def validate_policy_numbers(data) -> list[str]:
    """
    Validate policy_number format for each listing in data.
    Ignore "Pending" and "Exempt" listings.

    Args:
        data (list[tuple]): A list of tuples returned by create_listing_database()

    Returns:
        list[str]: A list of listing_id values whose policy numbers do NOT match the valid format
    """
    # TODO: Implement checkout logic following the instructions
    # ==============================
    # YOUR CODE STARTS HERE
    # ==============================
    
    pattern1 = re.compile(r"^20\d{2}-00\d{4}STR$")
    pattern2 = re.compile(r"^STR-000\d{4}$")

    invalid = []

    for row in data:
        listing_id = row[1]
        policy_number = row[2]
        if policy_number in ("Pending", "Exempt"):
            continue
        if not (pattern1.match(policy_number) or pattern2.match(policy_number)):
            invalid.append(listing_id)

    return invalid

    # ==============================
    # YOUR CODE ENDS HERE
    # ==============================


# EXTRA CREDIT
def google_scholar_searcher(query):
    """
    EXTRA CREDIT

    Args:
        query (str): The search query to be used on Google Scholar
    Returns:
        List of titles on the first page (list)
    """
    # TODO: Implement checkout logic following the instructions
    # ==============================
    # YOUR CODE STARTS HERE
    # ==============================
    pass
    # ==============================
    # YOUR CODE ENDS HERE
    # ==============================


class TestCases(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.search_results_path = os.path.join(self.base_dir, "html_files", "search_results.html")

        self.listings = load_listing_results(self.search_results_path)
        self.detailed_data = create_listing_database(self.search_results_path)

    def test_load_listing_results(self):
        # TODO: Check that the number of listings extracted is 18.
        # TODO: Check that the FIRST (title, id) tuple is  ("Loft in Mission District", "1944564").
        pass

    def test_get_listing_details(self):
        html_list = ["467507", "1550913", "1944564", "4614763", "6092596"]

        # TODO: Call get_listing_details() on each listing id above and save results in a list.

        # TODO: Spot-check a few known values by opening the corresponding listing_<id>.html files.
        # 1) Check that listing 467507 has the correct policy number "STR-0005349".
        # 2) Check that listing 1944564 has the correct host type "Superhost" and room type "Entire Room".
        # 3) Check that listing 1944564 has the correct location rating 4.9.
        pass

    def test_create_listing_database(self):
        # TODO: Check that each tuple in detailed_data has exactly 7 elements:
        # (listing_title, listing_id, policy_number, host_type, host_name, room_type, location_rating)

        # TODO: Spot-check the LAST tuple is ("Guest suite in Mission District", "467507", "STR-0005349", "Superhost", "Jennifer", "Entire Room", 4.8).
        pass

    def test_output_csv(self):
        out_path = os.path.join(self.base_dir, "test.csv")

        # TODO: Call output_csv() to write the detailed_data to a CSV file.
        # TODO: Read the CSV back in and store rows in a list.
        # TODO: Check that the first data row matches ["Guesthouse in San Francisco", "49591060", "STR-0000253", "Superhost", "Ingrid", "Entire Room", "5.0"].

        os.remove(out_path)

    def test_avg_location_rating_by_room_type(self):
        # TODO: Call avg_location_rating_by_room_type() and save the output.
        # TODO: Check that the average for "Private Room" is 4.9.
        pass

    def test_validate_policy_numbers(self):
        # TODO: Call validate_policy_numbers() on detailed_data and save the result into a variable invalid_listings.
        # TODO: Check that the list contains exactly "16204265" for this dataset.
        pass


def main():
    detailed_data = create_listing_database(os.path.join("html_files", "search_results.html"))
    output_csv(detailed_data, "airbnb_dataset.csv")


if __name__ == "__main__":
    main()
    unittest.main(verbosity=2)