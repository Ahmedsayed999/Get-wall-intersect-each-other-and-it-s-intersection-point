# ============================================================
# STRUCTURAL BEAM SPAN & SUPPORT ANALYSIS
# Dynamo Python + Revit API
# ============================================================

import clr

# Revit API
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# Revit Services
clr.AddReference("RevitServices")
from RevitServices.Persistence import DocumentManager

# Current Revit document
doc = DocumentManager.Instance.CurrentDBDocument


# ============================================================
# SETTINGS
# ============================================================

# Maximum distance between beam endpoint and column
# to consider the beam endpoint supported.
# Revit internal units = feet
SUPPORT_TOLERANCE_MM = 100.0

# Convert mm to Revit internal feet
SUPPORT_TOLERANCE = SUPPORT_TOLERANCE_MM / 304.8


# ============================================================
# COLLECT STRUCTURAL BEAMS
# ============================================================

beams = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralFraming) \
    .WhereElementIsNotElementType() \
    .ToElements()


# ============================================================
# COLLECT STRUCTURAL COLUMNS
# ============================================================

columns = FilteredElementCollector(doc) \
    .OfCategory(BuiltInCategory.OST_StructuralColumns) \
    .WhereElementIsNotElementType() \
    .ToElements()


# ============================================================
# FUNCTION:
# GET ELEMENT LOCATION POINT
# ============================================================

def get_element_point(element):

    location = element.Location

    # If the element has a LocationPoint
    if isinstance(location, LocationPoint):
        return location.Point

    # If the element has a LocationCurve
    elif isinstance(location, LocationCurve):
        curve = location.Curve

        if curve is not None:
            return curve.Evaluate(0.5, True)

    return None


# ============================================================
# FUNCTION:
# GET COLUMN BOUNDING BOX
# ============================================================

def get_column_bbox(column):

    bbox = column.get_BoundingBox(None)

    if bbox is None:
        return None

    return bbox


# ============================================================
# FUNCTION:
# CHECK WHETHER COLUMN SUPPORTS BEAM END
# ============================================================

def find_supporting_column(point, columns):

    closest_column = None
    closest_distance = float("inf")

    for column in columns:

        bbox = get_column_bbox(column)

        if bbox is None:
            continue

        min_point = bbox.Min
        max_point = bbox.Max

        # Expand bounding box by tolerance
        min_x = min_point.X - SUPPORT_TOLERANCE
        min_y = min_point.Y - SUPPORT_TOLERANCE
        min_z = min_point.Z - SUPPORT_TOLERANCE

        max_x = max_point.X + SUPPORT_TOLERANCE
        max_y = max_point.Y + SUPPORT_TOLERANCE
        max_z = max_point.Z + SUPPORT_TOLERANCE

        # Check if beam endpoint is inside
        # the expanded column bounding box
        inside_x = min_x <= point.X <= max_x
        inside_y = min_y <= point.Y <= max_y
        inside_z = min_z <= point.Z <= max_z

        if inside_x and inside_y and inside_z:

            column_point = get_element_point(column)

            if column_point is None:
                continue

            distance = point.DistanceTo(column_point)

            if distance < closest_distance:

                closest_distance = distance
                closest_column = column

    return closest_column


# ============================================================
# RESULTS
# ============================================================

results = []


# ============================================================
# ANALYZE EACH BEAM
# ============================================================

for beam in beams:

    location = beam.Location

    # We need the beam LocationCurve
    if not isinstance(location, LocationCurve):
        continue

    curve = location.Curve

    if curve is None:
        continue

    # --------------------------------------------------------
    # GET BEAM ENDPOINTS
    # --------------------------------------------------------

    start_point = curve.GetEndPoint(0)
    end_point = curve.GetEndPoint(1)


    # --------------------------------------------------------
    # FIND SUPPORTS
    # --------------------------------------------------------

    start_column = find_supporting_column(
        start_point,
        columns
    )

    end_column = find_supporting_column(
        end_point,
        columns
    )


    # --------------------------------------------------------
    # DETERMINE SUPPORT CONDITION
    # --------------------------------------------------------

    if start_column is not None and end_column is not None:

        support_condition = "Both Ends Supported"

    elif start_column is not None or end_column is not None:

        support_condition = "One End Supported"

    else:

        support_condition = "No Ends Supported"


    # --------------------------------------------------------
    # CALCULATE SPAN
    # --------------------------------------------------------

    if start_column is not None and end_column is not None:

        start_support_point = get_element_point(start_column)
        end_support_point = get_element_point(end_column)

        if start_support_point is not None and end_support_point is not None:

            span = start_support_point.DistanceTo(
                end_support_point
            )

            span_mm = span * 304.8

        else:

            span_mm = None

    else:

        span_mm = None


    # --------------------------------------------------------
    # GET ELEMENT IDs
    # --------------------------------------------------------

    beam_id = beam.Id.IntegerValue

    if start_column is not None:
        start_column_id = start_column.Id.IntegerValue
    else:
        start_column_id = None

    if end_column is not None:
        end_column_id = end_column.Id.IntegerValue
    else:
        end_column_id = None


    # --------------------------------------------------------
    # CREATE RESULT
    # --------------------------------------------------------

    result = {
        "Beam ID": beam_id,
        "Start Point": start_point,
        "End Point": end_point,
        "Start Support": start_column_id,
        "End Support": end_column_id,
        "Support Condition": support_condition,
        "Span (mm)": span_mm
    }

    results.append(result)


# ============================================================
# OUTPUT
# ============================================================

OUT = results