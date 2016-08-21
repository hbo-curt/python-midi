def read_varlen(data):
    value=0
    while True:
        chr=ord(data.next())
        # shift last value up 7 bits and add masked chr
        value=(value<<7) + (chr&0x7f)
        # is the hi-bit set?
        if not (chr&0x80):
            return value

def write_varlen(value):
    chr1=chr(value&0x7F)
    value>>=7
    if value:
        chr2=chr((value&0x7F)|0x80)
        value>>=7
        if value:
            chr3=chr((value&0x7F)|0x80)
            value>>=7
            if value:
                chr4=chr((value&0x7F)|0x80)
                res=chr4+chr3+chr2+chr1
            else:
                res=chr3+chr2+chr1
        else:
            res=chr2+chr1
    else:
        res=chr1
    return res

def find(cmp, sequence):
    if cmp is not None:
        for o in sequence:
            if cmp(o):
                return o
    return None

def bisect_right(a, x, lo=0, hi=None, vof=None):
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e <= x, and all e in
    a[i:] have e > x.  So if x already appears in the list, a.insert(x) will
    insert just after the rightmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.
    """
    if lo<0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi=len(a)
    if vof is None:
        vof=lambda v: v
    while lo<hi:
        mid=(lo+hi)//2
        if x<vof(a[mid]):
            hi=mid
        else:
            lo=mid+1
    return lo

def bisect_left(a, x, lo=0, hi=None, vof=None):
    """Return the index where to insert item x in list a, assuming a is sorted.

    The return value i is such that all e in a[:i] have e < x, and all e in
    a[i:] have e >= x.  So if x already appears in the list, a.insert(x) will
    insert just before the leftmost x already there.

    Optional args lo (default 0) and hi (default len(a)) bound the
    slice of a to be searched.
    """
    if lo<0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi=len(a)
    if vof is None:
        vof=lambda v: v
    while lo<hi:
        mid=(lo+hi)//2
        if vof(a[mid])<x:
            lo=mid+1
        else:
            hi=mid
    return lo
