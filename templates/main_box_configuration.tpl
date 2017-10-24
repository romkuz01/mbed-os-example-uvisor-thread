static const UvisorBoxAclItem g_main_acl[] = {
{% for mmio_region in mmio_regions %}
{% if 'size' in mmio_region %}
    { (void *){{mmio_region['base']}}, {{mmio_region['size']}}, {{mmio_region['permissions']}} },
{% else %}
    { {{mmio_region['base']}}, sizeof(*{{mmio_region['base']}}), {{mmio_region['permissions']}} },
{% endif %}
{% endfor %}
};

UVISOR_SET_MODE_ACL({{spm_status}}, g_main_acl);
UVISOR_SET_PAGE_HEAP({{global_heap_page_size}}, {{global_heap_minimal_page_number}});
