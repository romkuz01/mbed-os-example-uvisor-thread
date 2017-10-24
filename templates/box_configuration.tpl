static const UvisorBoxAclItem acl[] = {
{% for mmio_region in mmio_regions %}
{% if 'size' in mmio_region %}
    { (void *){{mmio_region['base']}}, {{mmio_region['size']}}, {{mmio_region['permissions']}} },
{% else %}
    { {{mmio_region['base']}}, sizeof(*{{mmio_region['base']}}), {{mmio_region['permissions']}} },
{% endif %}
{% endfor %}
};

static void {{entry_point}}(const void *);

UVISOR_BOX_NAMESPACE("{{partition_name}}");
UVISOR_BOX_HEAPSIZE({{heap_size}});
UVISOR_BOX_MAIN({{entry_point}}, {{priority}}, {{stack_size}});
UVISOR_BOX_CONFIG({{partition_name}}, acl, {{stack_size}}, {{context_structure_name}});

#define uvisor_ctx (({{context_structure_name}} *) __uvisor_ctx)