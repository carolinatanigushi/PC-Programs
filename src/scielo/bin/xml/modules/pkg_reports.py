# coding=utf-8

import os
from datetime import datetime

import attributes
import article_reports
import article_utils
import xpchecker
import html_reports


log_items = []


class ArticlePackage(object):

    def __init__(self, articles):
        self.articles = articles
        self.compile_references()
        self._xml_name_sorted_by_order = None
        self._indexed_by_order = None

    @property
    def xml_name_sorted_by_order(self):
        if self._xml_name_sorted_by_order is None:
            self._xml_name_sorted_by_order = self.sort_xml_name_by_order()
        return self._xml_name_sorted_by_order

    def sort_xml_name_by_order(self):
        order_and_xml_name_items = {}
        for xml_name, doc in self.articles.items():
            _order = str(doc.order)
            if not _order in order_and_xml_name_items.keys():
                order_and_xml_name_items[_order] = []
            order_and_xml_name_items[_order].append(xml_name)

        sorted_items = []
        for order in sorted(order_and_xml_name_items.keys()):
            for item in order_and_xml_name_items[order]:
                sorted_items.append(item)
        return sorted_items

    @property
    def indexed_by_order(self):
        if self._indexed_by_order is None:
            self._indexed_by_order = self.index_by_order()
        return self._indexed_by_order

    def index_by_order(self):
        indexed = {}
        for xml_name, article in self.articles.items():
            _order = str(article.order)
            if not _order in indexed.keys():
                indexed[_order] = []
            indexed[_order].append(article)
        return indexed

    @property
    def compiled_affiliations(self):
        if self._compiled_affilitions is None:
            self._compiled_affilitions = self.compile_affiliations()
        return self._compiled_affilitions

    def compile_affiliations(self):
        evaluation = {}
        keys = ['authors without aff', 
                'authors with more than 1 affs', 
                'authors with invalid xref[@ref-type=aff]', 
                'incomplete affiliations']
        for k in keys:
            evaluation[k] = 0

        for xml_name, doc in self.articles.items():
            aff_ids = [aff.id for aff in doc.affiliations]
            for contrib in doc.contrib_names:
                if len(contrib.xref) == 0:
                    evaluation['authors without aff'] += 1
                elif len(contrib.xref) > 1:
                    valid_xref = [xref for xref in contrib.xref if xref in aff_ids]
                    if len(valid_xref) != len(contrib.xref):
                        evaluation['authors with invalid xref[@ref-type=aff]'] += 1
                    elif len(valid_xref) > 1:
                        evaluation['authors with more than 1 affs'] += 1
                    elif len(valid_xref) == 0:
                        evaluation['authors without aff'] += 1
            for aff in doc.affiliations:
                if None in [aff.id, aff.i_country, aff.norgname, aff.orgname, aff.city, aff.state, aff.country]:
                    evaluation['incomplete affiliations'] += 1
        return evaluation

    def compile_references(self):
        self.sources_and_reftypes = {}
        self.sources_at = {}
        self.reftype_and_sources = {}
        self.missing_source = []
        self.missing_year = []
        self.unusual_sources = []
        self.unusual_years = []
        for xml_name, doc in self.articles.items():
            for ref in doc.references:
                if not ref.source in self.sources_and_reftypes.keys():
                    self.sources_and_reftypes[ref.source] = {}
                if not ref.publication_type in self.sources_and_reftypes[ref.source].keys():
                    self.sources_and_reftypes[ref.source][ref.publication_type] = 0
                self.sources_and_reftypes[ref.source][ref.publication_type] += 1
                if not ref.source in self.sources_at.keys():
                    self.sources_at[ref.source] = []
                if not xml_name in self.sources_at[ref.source]:
                    self.sources_at[ref.source].append(ref.id + ' - ' + xml_name)
                if not ref.publication_type in self.reftype_and_sources.keys():
                    self.reftype_and_sources[ref.publication_type] = {}
                if not ref.source in self.reftype_and_sources[ref.publication_type].keys():
                    self.reftype_and_sources[ref.publication_type][ref.source] = 0
                self.reftype_and_sources[ref.publication_type][ref.source] += 1

                # year
                if ref.publication_type in attributes.BIBLIOMETRICS_USE:
                    if ref.year is None:
                        self.missing_year.append([ref.id, xml_name])
                    else:
                        numbers = len([n for n in ref.year if n.isdigit()])
                        not_numbers = len(ref.year) - numbers
                        if not_numbers > numbers:
                            self.unusual_years.append([ref.year, ref.id, xml_name])

                    if ref.source is None:
                        self.missing_source.append([ref.id, xml_name])
                    else:
                        numbers = len([n for n in ref.source if n.isdigit()])
                        not_numbers = len(ref.source) - numbers
                        if not_numbers < numbers:
                            self.unusual_sources.append([ref.source, ref.id, xml_name])
        self.bad_sources_and_reftypes = {source: reftypes for source, reftypes in self.sources_and_reftypes.items() if len(reftypes) > 1}

    def tabulate_languages(self):
        labels = ['name', 'toc section', '@article-type', 'article titles', 
            'abstracts', 'key words', '@xml:lang', 'versions']

        items = []
        for xml_name in self.xml_name_sorted_by_order:
            doc = self.articles[xml_name]
            values = []
            values.append(xml_name)
            values.append(doc.toc_section)
            values.append(doc.article_type)
            values.append(['[' + str(t.language) + '] ' + str(t.title) for t in doc.titles])
            values.append([t.language for t in doc.abstracts])
            k = {}
            for item in doc.keywords:
                if not item.get('l') in k.keys():
                    k[item.get('l')] = []
                k[item.get('l')].append(item.get('k'))
            values.append(k)
            values.append(doc.language)
            values.append(doc.trans_languages)
            items.append(label_values(labels, values))
        return (labels, items)

    def tabulate_dates(self):
        labels = ['name', '@article-type', 
        'received', 'accepted', 'receive to accepted (days)', 'article date', 'issue date', 'accepted to publication (days)', 'accepted to today (days)']

        items = []
        for xml_name in self.xml_name_sorted_by_order:
            doc = self.articles[xml_name]
            values = []
            values.append(xml_name)
            values.append(doc.article_type)
            values.append(article_utils.display_date(doc.received_dateiso))
            values.append(article_utils.display_date(doc.accepted_dateiso))
            values.append(str(doc.history_days))
            values.append(article_utils.display_date(doc.article_pub_dateiso))
            values.append(article_utils.display_date(doc.issue_pub_dateiso))
            values.append(str(doc.publication_days))
            values.append(str(doc.registration_days))
            items.append(label_values(labels, values))
        return (labels, items)

    def journal_and_issue_metadata(self, labels):
        invalid_xml_name_items = []
        pkg_metadata = {label: {} for label in labels}

        for xml_name, article in self.articles.items():
            if article.tree is None:
                invalid_xml_name_items.append(xml_name)
            else:
                art_data = article.summary()
                for label in labels:
                    pkg_metadata[label] = article_utils.add_new_value_to_index(pkg_metadata[label], art_data[label], xml_name)

        return (invalid_xml_name_items, pkg_metadata)

    def validate_articles_pkg_xml_and_data(self, org_manager, doc_files_info_items, dtd_files, validate_order, display_all, xc_actions=None):
        #FIXME
        self.pkg_stats = {}
        self.pkg_reports = {}
        self.pkg_fatal_errors = 0

        for xml_name, doc_files_info in doc_files_info_items.items():
            for f in [doc_files_info.dtd_report_filename, doc_files_info.style_report_filename, doc_files_info.data_report_filename, doc_files_info.pmc_style_report_filename]:
                if os.path.isfile(f):
                    os.unlink(f)

        print('Validating package: inicio')
        for xml_name in self.xml_name_sorted_by_order:
            doc = self.articles[xml_name]
            doc_files_info = doc_files_info_items[xml_name]

            new_name = doc_files_info.new_name
            print(new_name)
            register_log(new_name)

            skip = False
            if xc_actions is not None:
                skip = xc_actions[doc_files_info.xml_name] == 'skip-update'

            if skip:
                print(' -- skept')
            else:
                xml_filename = doc_files_info.new_xml_filename

                xml_f, xml_e, xml_w = validate_article_xml(xml_filename, dtd_files, doc_files_info.dtd_report_filename, doc_files_info.style_report_filename, doc_files_info.ctrl_filename, doc_files_info.err_filename, display_all is False)
                data_f, data_e, data_w = article_reports.validate_article_data(org_manager, doc, new_name, os.path.dirname(xml_filename), validate_order, display_all, doc_files_info.data_report_filename)

                self.pkg_fatal_errors += xml_f + data_f
                self.pkg_stats[new_name] = ((xml_f, xml_e, xml_w), (data_f, data_e, data_w))
                self.pkg_reports[new_name] = (doc_files_info.err_filename, doc_files_info.style_report_filename, doc_files_info.data_report_filename)

        print('Validating package: fim')


class ArticlesPkgReport(object):

    def __init__(self, package):
        self.package = package

    def validate_consistency(self, validate_order):
        toc_report = self.consistency_report(validate_order)
        toc_f, toc_e, toc_w = html_reports.statistics_numbers(toc_report)
        if toc_f + toc_e + toc_w == 0:
            toc_report = None

        return (toc_f, toc_e, toc_w, toc_report)

    def consistency_report(self, validate_order):
        equal_data = ['journal-title', 'journal id NLM', 'journal ISSN', 'publisher name', 'issue label', 'issue pub date', ]
        unique_data = ['order', 'doi', 'elocation id']
        unique_status = {'order': 'FATAL ERROR', 'doi': 'FATAL ERROR', 'elocation id': 'FATAL ERROR', 'fpage-and-seq': 'ERROR'}

        if not validate_order:
            unique_status['order'] = 'WARNING'

        invalid_xml_name_items, pkg_metadata = self.package.journal_and_issue_metadata(equal_data + unique_data)

        r = ''
        if len(invalid_xml_name_items) > 0:
            r += html_reports.tag('div', html_reports.format_message('FATAL ERROR: Invalid XML files.'))
            r += html_reports.tag('div', html_reports.format_list('', 'ol', invalid_xml_name_items, 'issue-problem'))

        for label in equal_data:
            if len(pkg_metadata[label]) > 1:
                part = html_reports.p_message('FATAL ERROR: same value for ' + label + ' is required for all the documents in the package')
                for found_value, xml_files in pkg_metadata[label].items():
                    part += html_reports.format_list('found ' + label + ' "' + html_reports.display_xml(found_value, html_reports.XML_WIDTH*0.6) + '" in:', 'ul', xml_files, 'issue-problem')
                r += part

        for label in unique_data:
            if len(pkg_metadata[label]) > 0 and len(pkg_metadata[label]) != len(self.package.articles):
                none = []
                duplicated = {}
                pages = {}
                for found_value, xml_files in pkg_metadata[label].items():
                    if found_value == 'None':
                        none = xml_files
                    else:
                        if len(xml_files) > 1:
                            duplicated[found_value] = xml_files
                        if label == 'fpage-and-seq':
                            v = found_value
                            if v.isdigit():
                                v = str(int(found_value))
                            if not v in pages.keys():
                                pages[v] = []
                            pages[v] += xml_files

                if len(pages) == 1 and '0' in pages.keys():
                    duplicated = []

                if len(duplicated) > 0:
                    part = html_reports.p_message(unique_status[label] + ': unique value of ' + label + ' is required for all the documents in the package')
                    for found_value, xml_files in duplicated.items():
                        part += html_reports.format_list('found ' + label + ' "' + found_value + '" in:', 'ul', xml_files, 'issue-problem')
                    r += part
                if len(none) > 0:
                    part = html_reports.p_message('INFO: there is no value for ' + label + '.')
                    part += html_reports.format_list('no value for ' + label + ' in:', 'ul', none, 'issue-problem')
                    r += part

        issue_common_data = ''
        for label in equal_data:
            message = ''
            if len(pkg_metadata[label].items()) == 1:
                issue_common_data += html_reports.display_labeled_value(label, pkg_metadata[label].keys()[0])
            else:
                message = '(ERROR: Unique value expected for ' + label + ')'
                issue_common_data += html_reports.format_list(label + message, 'ol', pkg_metadata[label].keys())
        return html_reports.tag('div', issue_common_data, 'issue-data') + html_reports.tag('div', r, 'issue-messages')

    def overview_report(self):
        r = ''
        r += html_reports.tag('h4', 'Languages overview')
        labels, items = self.package.tabulate_languages()
        r += html_reports.sheet(labels, items, 'dbstatus')

        r += html_reports.tag('h4', 'Dates overview')
        labels, items = self.package.tabulate_dates()
        r += html_reports.sheet(labels, items, 'dbstatus')

        r += html_reports.tag('h4', 'Affiliations overview')
        items = []
        affs_compiled = self.package.compile_affiliations()
        for label, q in affs_compiled.items():
            items.append({'label': label, 'quantity': str(q)})
        r += html_reports.sheet(['label', 'quantity'], items, 'dbstatus')
        return r

    def references_overview_report(self):
        labels = ['label', 'status', 'message']
        items = []

        values = []
        values.append('references by type')
        values.append('INFO')
        values.append({reftype: str(sum(sources.values())) for reftype, sources in self.package.reftype_and_sources.items()})
        items.append(label_values(labels, values))

        #message = {source: reftypes for source, reftypes in sources_and_reftypes.items() if len(reftypes) > 1}}
        if len(self.package.bad_sources_and_reftypes) > 0:
            values = []
            values.append('same sources as different types')
            values.append('ERROR')
            values.append(self.package.bad_sources_and_reftypes)
            items.append(label_values(labels, values))
            values = []
            values.append('same sources as different types references')
            values.append('INFO')
            values.append({source: self.package.sources_at.get(source) for source in self.package.bad_sources_and_reftypes.keys()})
            items.append(label_values(labels, values))

        if len(self.package.missing_source) > 0:
            items.append({'label': 'references missing source', 'status': 'ERROR', 'message': [' - '.join(item) for item in self.package.missing_source]})
        if len(self.package.missing_year) > 0:
            items.append({'label': 'references missing year', 'status': 'ERROR', 'message': [' - '.join(item) for item in self.package.missing_year]})
        if len(self.package.unusual_sources) > 0:
            items.append({'label': 'references with unusual value for source', 'status': 'ERROR', 'message': [' - '.join(item) for item in self.package.unusual_sources]})
        if len(self.package.unusual_years) > 0:
            items.append({'label': 'references with unusual value for year', 'status': 'ERROR', 'message': [' - '.join(item) for item in self.package.unusual_years]})

        return html_reports.tag('h4', 'Package references overview') + html_reports.sheet(labels, items, table_style='dbstatus')

    def detail_report(self, conversion_reports=None):
        labels = ['name', 'order', 'fpage', 'doi', 'aop pid', 'toc section', '@article-type', 'article title', 'reports']
        items = []

        n = '/' + str(len(self.package.articles))
        validations_text = ''
        index = 0

        for new_name in self.package.xml_name_sorted_by_order:
            index += 1
            item_label = str(index) + n + ' - ' + new_name
            print(item_label)

            xml_f, xml_e, xml_w = self.package.pkg_stats[new_name][0]
            data_f, data_e, data_w = self.package.pkg_stats[new_name][1]
            rep1, rep2, rep3 = self.package.pkg_reports[new_name]

            links = ''
            block = ''
            if xml_f + xml_e + xml_w > 0:
                t = []
                v = []
                for rep in [rep1, rep2]:
                    content = get_report_text(rep)
                    if len(content) > 0:
                        t.append(os.path.basename(rep))
                        v.append(content)
                content = ''.join(v)
                status = html_reports.get_stats_numbers_style(xml_f, xml_e, xml_w)
                links += html_reports.report_link('xmlrep' + new_name, '[ XML Validations ]', 'xmlrep')
                block += html_reports.report_block('xmlrep' + new_name, content, 'xmlrep')

            if data_f + data_e + data_w > 0:
                status = html_reports.get_stats_numbers_style(data_f, data_e, data_w)
                links += html_reports.report_link('datarep' + new_name, '[ Data Quality Control ]', 'datarep')
                block += html_reports.report_block('datarep' + new_name, get_report_text(rep3), 'datarep')

            if conversion_reports is not None:
                r = conversion_reports.get(new_name)
                if r is not None:
                    conv_f, conv_e, conv_w, conv_rep = r
                    status = html_reports.get_stats_numbers_style(conv_f, conv_e, conv_w)
                    links += html_reports.report_link('xcrep' + new_name, '[ Converter ]', 'xcrep')
                    block += html_reports.report_block('xcrep' + new_name, conv_rep, 'xcrep')

            values = []
            values.append(new_name)
            values.append(self.package.articles[new_name].order)
            values.append(self.package.articles[new_name].fpage)
            values.append(self.package.articles[new_name].doi)
            values.append(self.package.articles[new_name].previous_pid)
            values.append(self.package.articles[new_name].toc_section)
            values.append(self.package.articles[new_name].article_type)
            values.append(self.package.articles[new_name].title)
            values.append(links)

            items.append(label_values(labels, values))
            items.append({'reports': block})

        return html_reports.sheet(labels, items, table_style='reports-sheet', html_cell_content=['reports'])

    def sources_overview_report(self):
        labels = ['source', 'total']
        h = None
        if len(self.package.reftype_and_sources) > 0:
            h = ''
            for reftype, sources in self.package.reftype_and_sources.items():
                items = []
                h += html_reports.tag('h4', reftype)
                for source in sorted(sources.keys()):
                    items.append({'source': source, 'total': str(sources[source])})
                h += html_reports.sheet(labels, items, 'dbstatus')
        return h


def register_log(text):
    log_items.append(datetime.now().isoformat() + ' ' + text)


def update_err_filename(err_filename, dtd_report):
    if os.path.isfile(dtd_report):
        separator = ''
        if os.path.isfile(err_filename):
            separator = '\n\n\n' + '.........\n\n\n'
        open(err_filename, 'a+').write(separator + 'DTD errors\n' + '-'*len('DTD errors') + '\n' + open(dtd_report, 'r').read())


def delete_irrelevant_reports(ctrl_filename, is_valid_style, dtd_validation_report, style_checker_report):
    if ctrl_filename is None:
        if is_valid_style is True:
            os.unlink(style_checker_report)
    else:
        open(ctrl_filename, 'w').write('Finished')
    if os.path.isfile(dtd_validation_report):
        os.unlink(dtd_validation_report)


def validate_article_xml(xml_filename, dtd_files, dtd_report, style_report, ctrl_filename, err_filename, run_background):

    xml, valid_dtd, valid_style = xpchecker.validate_article_xml(xml_filename, dtd_files, dtd_report, style_report, run_background)
    f, e, w = valid_style
    update_err_filename(err_filename, dtd_report)
    if xml is None:
        f += 1
    if not valid_dtd:
        f += 1
    delete_irrelevant_reports(ctrl_filename, f + e + w == 0, dtd_report, style_report)
    return (f, e, w)


def get_report_text(filename):
    report = ''
    if os.path.isfile(filename):
        content = open(filename, 'r').read()
        if not isinstance(content, unicode):
            content = content.decode('utf-8')
        if 'Parse/validation finished' in content and '<!DOCTYPE' in content:
            part1 = content[0:content.find('<!DOCTYPE')]
            part2 = content[content.find('<!DOCTYPE'):]

            l = part1[part1.rfind('Line number:')+len('Line number:'):]
            l = l[0:l.find('Column')]
            l = ''.join([item.strip() for item in l.split()])
            if l.isdigit():
                l = str(int(l) + 1) + ':'
                if l in part2:
                    part2 = part2[0:part2.find(l)] + '\n...'

            part1 = part1.replace('\n', '<br/>')
            part2 = part2.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>').replace('\t', '&nbsp;'*4)
            report = part1 + part2
        elif '</body>' in content:
            content = content[content.find('<body'):]
            content = content[0:content.rfind('</body>')]
            report = content[content.find('>')+1:]
        elif '<body' in content:
            content = content[content.find('<body'):]
            report = content[content.find('>')+1:]
        else:
            report = ''
    return report


def sum_stats(stats_items):
    f = sum([i[0] for i in stats_items])
    e = sum([i[1] for i in stats_items])
    w = sum([i[2] for i in stats_items])
    return (f, e, w)


def xml_list(pkg_path, xml_filenames=None):
    r = ''
    r += '<p>XML path: ' + pkg_path + '</p>'
    if xml_filenames is None:
        xml_filenames = [pkg_path + '/' + name for name in os.listdir(pkg_path) if name.endswith('.xml')]
    r += '<p>Total of XML files: ' + str(len(xml_filenames)) + '</p>'
    r += html_reports.format_list('', 'ol', [os.path.basename(f) for f in xml_filenames])
    return '<div class="xmllist">' + r + '</div>'


def error_msg_subtitle():
    msg = html_reports.tag('p', 'Fatal error - indicates errors which impact on the quality of the bibliometric indicators and other services')
    msg += html_reports.tag('p', 'Error - indicates the other kinds of errors')
    msg += html_reports.tag('p', 'Warning - indicates that something can be an error or something needs more attention')
    return html_reports.tag('div', msg, 'subtitle')


def label_values(labels, values):
    r = {}
    for i in range(0, len(labels)):
        r[labels[i]] = values[i]
    return r


def articles_sorted_by_order(articles):
    sorted_by_order = {}
    for xml_name, article in articles.items():
        try:
            _order = article.order
        except:
            _order = 'None'
        if not _order in sorted_by_order.keys():
            sorted_by_order[_order] = []
        sorted_by_order[_order].append(article)
    return sorted_by_order


def sorted_xml_name_by_order(articles):
    order_and_xml_name_items = {}
    for xml_name, article in articles.items():
        if article.tree is None:
            _order = 'None'
        else:
            _order = article.order
        if not _order in order_and_xml_name_items.keys():
            order_and_xml_name_items[_order] = []
        order_and_xml_name_items[_order].append(xml_name)

    sorted_items = []
    for order in sorted(order_and_xml_name_items.keys()):
        for item in order_and_xml_name_items[order]:
            sorted_items.append(item)
    return sorted_items


def processing_result_location(result_path):
    return '<h5>Result of the processing: </h5>' + '<p>' + html_reports.link('file:///' + result_path, result_path) + '</p>'


def save_report(filename, title, content):
    html_reports.save(filename, title, content)
    print('\n\nReport:\n ' + filename)


def display_report(report_filename):
    try:
        os.system('python -mwebbrowser file:///' + report_filename.replace('//', '/'))
    except:
        pass


def statistics_and_subtitle(f, e, w):
    x = error_msg_subtitle()
    x += html_reports.statistics_display(f, e, w, False)
    return x


def format_complete_report(report_components):
    content = ''
    order = ['summary-report', 'detail-report', 'xml-files', 'pkg_overview', 'db-overview', 'issue-not-registered', 'toc', 'references']
    labels = {
        'summary-report': 'Summary report', 
        'detail-report': 'Detail report', 
        'xml-files': 'Files/Folders',
        'db-overview': 'Database overview',
        'pkg_overview': 'Package overview',
        'references': 'Sources'
    }
    f, e, w = html_reports.statistics_numbers(html_reports.join_texts(report_components.values()))
    report_components['summary-report'] = statistics_and_subtitle(f, e, w) + report_components.get('summary-report', '')

    content += html_reports.tabs_items([(tab_id, labels[tab_id]) for tab_id in order if report_components.get(tab_id) is not None], 'summary-report')
    for tab_id in order:
        c = report_components.get(tab_id)
        if c is not None:
            style = 'selected-tab-content' if tab_id == 'summary-report' else 'not-selected-tab-content'
            content += html_reports.tab_block(tab_id, c, style)

    content += html_reports.tag('p', 'Finished.')
    return (f, e, w, content)
