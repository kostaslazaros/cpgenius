import pandas as pd
from pathlib import Path

# Function to assign a rank to each element in a list with the first element being the most important.
def rank_list(lst:list)->dict:
    # Returns a dictionary comprehension where each list element is a key and its rank is a value.
    # The rank is calculated as the length of the list minus one minus the element's index.
    return {elm:len(lst) - 1 - i for i, elm in enumerate(lst)}


# Function to perform Borda count aggregation for a list of ranked lists.
def borda_aggregation(loflists: list[list]) -> dict:
    # Convert each individual list into a dictionary of ranks.
    list_ranks = [rank_list(l) for l in loflists]
    # Create a set of all unique elements across all the lists.
    feature_set = {i for i in [el for nl in loflists for el in nl]}
    # Return a dictionary where each element's score is the sum of its ranks across all the lists.
    return {e:sum([lr.get(e, 0) for lr in list_ranks]) for e in feature_set}


# Function to create a sorted DataFrame from a dictionary of results.
def create_sorted_df(result:dict):
    # Create a DataFrame from the dictionary.
    df = pd.DataFrame(list(result.items()), columns=['Feature', 'Borda Rank'])
    # Sort the DataFrame based on the 'Borda Rank' column in descending order.
    df.sort_values(by='Borda Rank', ascending=False, inplace=True)
    # Reset the DataFrame's index and drop the old index.
    df.reset_index(drop=True, inplace=True)
    # Return the sorted DataFrame.
    return df


# Function to create a DataFrame from a list of lists using Borda count aggregation.
def borda_df(loflists: list[list]):
    # Aggregate the lists into a Borda count dictionary.
    borda_dict = borda_aggregation(loflists)
    # Create and return a sorted DataFrame from the Borda count dictionary.
    return create_sorted_df(borda_dict)


def collect_feature_lists(path=".", pattern="ranked_features_*.csv", column="Feature", verbose=True):
    """
    Find CSVs by pattern, read the given column, and return a list-of-lists plus the file list.
    Keeps order and duplicates exactly as in the CSVs (matching your rank_list behavior).
    """
    data_dir = Path(path)
    files = sorted(data_dir.glob(pattern))
    if verbose:
        print(f"Found {len(files)} files in {data_dir.resolve()} matching '{pattern}':")
        for f in files:
            print(" -", f.name)

    feature_lsts = []
    for f in files:
        s = pd.read_csv(f, usecols=[column])[column]
        lst = s.tolist()  # no cleanup, preserve as-is
        feature_lsts.append(lst)
        if verbose:
            print(f"{f.name}: {len(lst)} features")

    if verbose:
        print(f"\nTotal lists collected: {len(feature_lsts)}")

    return feature_lsts, files


def borda_from_folder(path=".", pattern="ranked_features_*.csv", column="Feature", verbose=True):
    """
    Uses your borda_df() to aggregate all ranked lists found in a folder.
    Returns (df, files, feature_lsts).
    """
    feature_lsts, files = collect_feature_lists(path, pattern, column, verbose=verbose)
    df = borda_df(feature_lsts)  # uses YOUR function
    return df   