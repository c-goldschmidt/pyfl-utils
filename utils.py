def concat_lists(list1, list2):
    if not list1:
        return list2
    if not isinstance(list1, list):
        list1 = [list1]
    if not isinstance(list2, list):
        list2 = [list2]
    return list1 + list2
