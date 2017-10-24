#ifndef COMMON_CONFIGURATION_H
#define COMMON_CONFIGURATION_H

/* Check all the defined MMIO regions for overlapping. */
{% for region_pair in region_pair_list %}
{% if 'size' in region_pair['region1'] and 'size' in region_pair['region2'] %}
static_assert(
    ({{region_pair['region1']['base']}} + {{region_pair['region1']['size']}} - 1 < {{region_pair['region2']['base']}}) ||
    ({{region_pair['region2']['base']}} + {{region_pair['region2']['size']}} - 1 < {{region_pair['region1']['base']}}),
    "The region with base {{region_pair['region1']['base']}} and size {{region_pair['region1']['size']}} overlaps with the region with base {{region_pair['region2']['base']}} and size {{region_pair['region2']['size']}}!");
{% endif %}
{% if 'size' in region_pair['region1'] and not 'size' in region_pair['region2'] %}
static_assert(
    ({{region_pair['region1']['base']}} + {{region_pair['region1']['size']}} - 1 < (uint32_t){{region_pair['region2']['base']}}) ||
    ((uint32_t){{region_pair['region2']['base']}} + sizeof(*{{region_pair['region2']['base']}}) - 1 < {{region_pair['region1']['base']}}),
    "The region with base {{region_pair['region1']['base']}} and size {{region_pair['region1']['size']}} overlaps with the region {{region_pair['region2']['base']}}!");
{% endif %}
{% if not 'size' in region_pair['region1'] and 'size' in region_pair['region2'] %}
static_assert(
    ((uint32_t){{region_pair['region1']['base']}} + sizeof(*{{region_pair['region1']['base']}}) - 1 < {{region_pair['region2']['base']}}) ||
    ({{region_pair['region2']['base']}} + {{region_pair['region2']['size']}} - 1 < (uint32_t){{region_pair['region1']['base']}}),
    "The region {{region_pair['region1']['base']}} overlaps with the region with base {{region_pair['region2']['base']}} and size {{region_pair['region2']['size']}}!");
{% endif %}
{% if not 'size' in region_pair['region1'] and not 'size' in region_pair['region2'] %}
static_assert(
    ((uint32_t){{region_pair['region1']['base']}} + sizeof(*{{region_pair['region1']['base']}}) - 1 < (uint32_t){{region_pair['region2']['base']}}) ||
    ((uint32_t){{region_pair['region2']['base']}} + sizeof(*{{region_pair['region2']['base']}}) - 1 < (uint32_t){{region_pair['region1']['base']}}),
    "The region {{region_pair['region1']['base']}} overlaps with the region {{region_pair['region2']['base']}}!");
{% endif %}

{% endfor %}
#endif