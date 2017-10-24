#!/usr/bin/python
import argparse
import sys
import os
import re
import fnmatch
import logging
from lxml import etree
from jinja2 import Environment, FileSystemLoader
from argparse_action_helper import StoreInputDir
from argparse_action_helper import StoreOutputDir

script_dir = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger('uVisor')

def to_number(num_str, error_message):
    """
    Convert a given string to an integer
    :param num_str: number string
    """

    radix = 16 if num_str.startswith('0x') else 10
    try:
        return int(num_str, radix)
    except:
        logger.error(error_message)
        raise

def find_manifest_files(start_dir):
    """
    Find all the manifest files in the current directory tree.
    The current convention is to name the manifest files as 'box_*.xml'
    with the main box file named 'box_main.xml'.
    :param start_dir: root directory to search
    """

    manifest_files = []
    for dirpath, dirnames, filenames in os.walk(start_dir):
        for filename in fnmatch.filter(filenames, 'box_*.xml'):
            manifest_files.append(os.path.join(dirpath, filename))
    return manifest_files


def read_manifest_file(manifest_file):
    """
    Load partition manifest file and construct a dictionary from it while
    validating the file contents
    :param manifest_file: manifest file name with a path
    """

    # Load partition manifest file.
    manifest = etree.parse(manifest_file, etree.XMLParser(dtd_validation=True)).getroot()

    # Define partition dictionary.
    stack_size_str = manifest.find('stack').get('size')
    heap_size_str = manifest.find('heap').get('size')
    partition = {
        'file': manifest_file,

        'partition_name': manifest.get('name'),
        'priority': manifest.get('priority'),
        'entry_point': manifest.find('code').get('entry_point'),
        'stack_size': to_number(stack_size_str,
            'Stack size in "%s" must be a number, "%s" given.' % (manifest_file, stack_size_str)),
        'heap_size': to_number(heap_size_str,
            'Heap size in "%s" must be a number, "%s" given.' % (manifest_file, heap_size_str)),

        # The next field is only relevant for the current uVisor implementation, should be
        # removed in the future.
        'context_structure_name': manifest.find('context_structure_name').text,
    }

    # Parse MMIO sections if present.
    mmio = manifest.find('mmio')
    mmio_region_list = []

    # Named MMIO regions.
    mmio_regions_named = mmio.findall('mmioregion_named') if mmio is not None else []
    for mmio_region in mmio_regions_named:
        region_description = {
            'base': mmio_region.get('base'),
            'permissions': mmio_region.get('permissions')
        }
        mmio_region_list.append(region_description)

    # Numeric MMIO regions.
    mmio_regions = mmio.findall('mmioregion') if mmio is not None else []
    for mmio_region in mmio_regions:
        base_str = mmio_region.get('base')
        size_str = mmio_region.get('size')
        region_description = {
            'base': to_number(base_str,
                'MMIO region base in "%s" must be a number, "%s" given.' % (manifest_file, base_str)),
            'size': to_number(size_str,
                'MMIO region size in "%s" must be a number, "%s" given.' % (manifest_file, size_str)),
            'permissions': mmio_region.get('permissions')
        }
        mmio_region_list.append(region_description)

    if mmio_region_list:
        partition['mmio_regions'] = mmio_region_list

    # Parse the SFIDs.
    sfids = manifest.findall('sfid')
    sfid_list = [sfid.text for sfid in sfids]
    if sfid_list:
        partition['sfids'] = sfid_list

    # Parse the source file list and check the files for existence.
    src_files  = manifest.find('src').findall('filename')
    src_file_list = [src_file.text for src_file in src_files]

    manifest_file_dir = os.path.dirname(manifest_file)
    for src_file in src_file_list:
        src_file_path = os.path.join(manifest_file_dir, src_file)
        if not os.path.isfile(src_file_path):
            raise ValueError('The source file "%s" mentioned in "%s" doesn\'t exist.' % (src_file, manifest_file))

    partition['src_files'] = src_file_list

    # Parse the IRQs.
    irqs = manifest.findall('irq_num')
    irq_list = []
    for irq in irqs:
        irq_num = to_number(irq.text, 'IRQ in "%s" must be a number, "%s" given.' % (manifest_file, irq.text))
        irq_list.append(irq_num)
    if irq_list:
        partition['irqs'] = irq_list

    # Parse SFID dependencies.
    extern_sfids = manifest.findall('extern_sfid')
    extern_sfid_list = [sfid.text for sfid in extern_sfids]
    if extern_sfid_list:
        partition['extern_sfids'] = extern_sfid_list

    # The following fields are only relevant for the current uVisor implementation, should be
    # removed in the future.
    spm_status = manifest.find('spm_status')
    if spm_status is not None:
        partition['spm_status'] = spm_status.text

    global_heap = manifest.find('global_heap')
    if global_heap is not None:
        page_size = global_heap.get('page_size')
        partition['global_heap_page_size'] = to_number(page_size,
            'Global heap page size in "%s" must be a number, "%s" given.' % (manifest_file, page_size))
        minimal_page_number = global_heap.get('minimal_page_number')
        partition['global_heap_minimal_page_number'] = to_number(minimal_page_number,
            'Global heap minimal page number in "%s" must be a number, "%s" given.' %
            (manifest_file, minimal_page_number))

    return partition

def validate_partition_manifests(manifests):
    """
    Checks the correctness of the manifest file list (no conflicts, no missing elements, etc.)
    :param manifests: a list of the partition manifests
    """

    # Make sure the partition names are unique.
    start = 1
    for manifest1 in manifests[:-1]:
        for manifest2 in manifests[start:]:
            if manifest1['partition_name'] == manifest2['partition_name']:
                raise ValueError('Partition name "%s" is not unique, found in both "%s" and "%s".' %
                                     (manifest1['partition_name'], manifest1['file'], manifest2['file']))
        start += 1

    # Make sure all the SFIDs are unique,
    # construct a list of all the SFIDs first (will be also used for SFID dependency checks).
    sfids = [];
    for manifest in manifests:
        if 'sfids' in manifest:
            for sfid in manifest['sfids']:
                sfids.append({'sfid': sfid, 'file': manifest['file']})

    start = 1
    for sfid1 in sfids[:-1]:
        for sfid2 in sfids[start:]:
            if sfid1['sfid'] == sfid2['sfid']:
                raise ValueError('SFID declaration "%s" is found in both "%s" and "%s".' %
                                     (sfid1['sfid'], sfid1['file'], sfid2['file']))
        start += 1

    # Check for IRQ conflicts.
    start = 1
    for manifest1 in manifests[:-1]:
        for manifest2 in manifests[start:]:
            if 'irqs' in manifest1 and 'irqs' in manifest2:
                irqs1 = manifest1['irqs']
                irqs2 = manifest2['irqs']
                for irq1 in irqs1:
                    for irq2 in irqs2:
                        if irq1 == irq2:
                            raise ValueError('IRQ %d (0x%x) is required by both "%s" and "%s".' %
                                                 (irq1, irq1, manifest1['file'], manifest2['file']))
        start += 1

    # Check that all the external SFIDs can be found.
    declared_sfids = set([sfid['sfid'] for sfid in sfids])
    for manifest in manifests:
        if 'extern_sfids' in manifest:
            missing_sfids = set(manifest['extern_sfids']) - declared_sfids
            if missing_sfids:
                raise ValueError('External SFID(s) "%s" required by "%s" can\'t be found in any partition manifest.' %
                                 ('", "'.join(missing_sfids), manifest['file']))


def generate_common_code(manifests, code_template, output_dir):
    """
    Geneartes C code from the manifest files using a given template
    :param manifests: parsed manifest files that passed initial checks
    """

    # Create a list of all the defined MMIO regions.
    region_list = []
    for manifest in manifests:
        if 'mmio_regions' in manifest:
            region_list += manifest['mmio_regions']

    # Create a list of all the MMIO region pairs that will be
    # used for overlap checks.
    region_pair_list = []
    if len(region_list) > 1:
        start = 1
        for region1 in region_list[:-1]:
            for region2 in region_list[start:]:
                region_pair_list.append({'region1': region1, 'region2': region2})
            start += 1

    # Render the template.
    rendered_template = code_template.render(region_pair_list=region_pair_list)

    # Generate the code file for inclusion.
    rendered_filename = os.path.join(output_dir, 'partition_common.inc')

    with open(rendered_filename, 'w') as rendered_file:
        rendered_file.write(rendered_template)

def generate_partition_code(manifest, code_template, output_dir):
    """
    Genearte C code from the manifest file using a given template
    :param manifest_file: manifest file name with a path
    :param box_configuration_template: configuration template file name
    :param output_dir: a directory for the generated C files
    """

    # Render the template.
    rendered_template = code_template.render(manifest)

    # Generate the code file for inclusion.
    rendered_filename = os.path.join(output_dir, 'partition_description_' + manifest['partition_name'] + '.inc')

    with open(rendered_filename, 'w') as rendered_file:
        rendered_file.write(rendered_template)


def process_manifest_files(manifest_files, output_dir):
    """
    Process all the given manifest files
    :param manifest_files: a list of manifest files
    :param output_dir: a directory for the generated C files
    """

    # Construct a list of all the manifests.
    manifests = [read_manifest_file(manifest_file) for manifest_file in manifest_files]

    # Validate the correctness of the manifest collection.
    validate_partition_manifests(manifests)

    # Load templates for the code generation.
    env = Environment(
        loader=FileSystemLoader(os.path.join(script_dir, 'templates')),
        lstrip_blocks=True,
        trim_blocks=True
    )

    # Generate common code.
    generate_common_code(manifests, env.get_template('common_configuration.tpl'), output_dir)

    # Generate per-partition code.
    for manifest in manifests:
        if os.path.basename(manifest['file']) == 'box_main.xml':
            code_template = env.get_template('main_box_configuration.tpl')
        else:
            code_template = env.get_template('box_configuration.tpl')
        generate_partition_code(manifest, code_template, output_dir)


def main():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description='Generate partition code from PSA manifest files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'workspace',
        action=StoreInputDir,
        help='Workspace root directory that is searched for PSA manifest files'
    )

    parser.add_argument(
        'output_dir',
        action=StoreOutputDir,
        help='Output directory for the generated source files'
    )

    args = parser.parse_args()

    process_manifest_files(find_manifest_files(args.workspace), args.output_dir)


if __name__ == '__main__':
    main()
