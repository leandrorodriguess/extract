# -*- coding: utf-8 -*-

from collections import OrderedDict

import pandas as pd
from pandas.core.common import flatten

from data_tables.util import create_adjacency_matrix, create_weighted_matrix
from util.util import similaridade_entre_cadeias


class BasicProduction:
    columns = ['ano', 'titulo', 'autores', 'relevante', 'natureza']

    mapping_attribute_path = {
        'autores': 'AUTORES/@NOME-PARA-CITACAO',
        'ano': "*[starts-with(local-name(), 'DADOS-BASICOS')]/@*[starts-with(local-name(), 'ANO')]",
        'titulo': "*[starts-with(local-name(), 'DADOS-BASICOS')]/@*[starts-with(local-name(), 'TITULO') and not(contains(local-name(), 'INGLES'))]",
        'relevante': "*[starts-with(local-name(), 'DADOS-BASICOS')]/@FLAG-RELEVANCIA",
        'natureza': "*[starts-with(local-name(), 'DADOS-BASICOS')]/@NATUREZA"
    }

    array_columns = ['autores']

    # id = None
    data_frame = pd.DataFrame()
    adjacency_matrix = None
    weighted_matrix = None

    def __init__(self, id, initial_data_frame=None, group_similar=False, timespan=None):
        """
        :param initial_data_frame: initial content to be added
        :param group_similar: whether similar entries (by is_similar) should be ignored; if True, the column 'id_membro' is converted to frozenset and
        its values from similar entries are united.
        :param timespan: should be a single pair tuple (since_year, until_year) or a list of such tuples (in this case, items will be dropped from the data
        frame only if they don't fall inside any of the spans).
        :return:
        """
        self.id = id
        self.group_similar = group_similar
        self.timespan = timespan
        self.data_frame = pd.DataFrame(columns=self.columns)
        self.data_frame['ano'] = pd.to_numeric(self.data_frame['ano'])
        if initial_data_frame is not None:
            self.data_frame = self.data_frame.append(initial_data_frame, ignore_index=True)

    def add_from_parser(self, productions_list, **kwargs):
        raise Exception("Método inutilizado; suporte a HTML atualmente descontinuado")

    def add_from_xml_elements(self, elements_list, **kwargs):
        """
        Add a list of productions from an XML element (passed by a parser).
        :param elements_list: list of XML elements corresponding to productions to add
        :param kwargs: extra columns to set a fixed value (key: value -> df[key] = value)
        :return: self, to allow nesting calls
        """
        assert self.adjacency_matrix is None
        productions_df = self._df_from_xml_parser(elements_list)
        productions_df['id_membro'] = self.id
        for key, value in kwargs.items():
            productions_df[key] = value
        self.append_data(productions_df)
        return self

    def _df_from_xml_parser(self, elements_list):
        productions = {}
        for column in self.columns:
            path = column
            if column in self.mapping_attribute_path:
                path = self.mapping_attribute_path[column]
            values = [element.xpath(path) for element in elements_list]
            if column not in self.array_columns:
                # productions[column] = tuple(flatten(values))
                productions[column] = tuple(map(lambda x: x[0] if x else None, values))
            else:
                # FIXME: usar lista para não perder estrutura (problema: template ordena por autores, o que causa erro quando é uma lista)
                # productions[column] = values
                productions[column] = tuple(map('; '.join, values))
        return pd.DataFrame(productions)

    def append(self, productions):
        if productions:
            self.append_data(productions.data_frame)

    def append_data(self, productions_df):
        assert self.adjacency_matrix is None
        # assert isinstance(productions, type(self)) or isinstance(productions, pd.DataFrame)
        # if isinstance(productions, type(self)):
        #     # self.data_frame = self.data_frame.append(productions.data_frame, ignore_index=True)
        #     data_frame_to_append = productions.data_frame
        # # elif isinstance(productions, pd.DataFrame):
        # else:
        #     # self.data_frame = self.data_frame.append(productions, ignore_index=True)
        #     data_frame_to_append = productions
        data_frame_to_append = productions_df

        # Filter by timespan
        # TODO: make this dynamic, when porting to a web framework
        if self.timespan:
            data_frame_to_append['ano'] = pd.to_numeric(data_frame_to_append['ano'])
            if isinstance(self.timespan, list):  # So this is a set of non-exclusive timespans (defined in the list, not the config)
                matched_years = pd.Series([False] * len(data_frame_to_append.ano))
                for timespan in self.timespan:
                    matched_years |= (data_frame_to_append.ano >= timespan[0]) & (data_frame_to_append.ano <= timespan[1])
                data_frame_to_append = data_frame_to_append[matched_years]
            else:
                data_frame_to_append = data_frame_to_append[(data_frame_to_append.ano >= self.timespan[0]) & (data_frame_to_append.ano <= self.timespan[1])]

        # Deal with duplicated entries
        if self.group_similar:
            duplicated = []
            for i, row in data_frame_to_append.iterrows():
                similar = self.data_frame.apply(lambda x: self.is_similar(x, row), axis=1)
                if similar.any().any():  # double any's because on empty similar any returns bool by column
                    duplicated.append(i)
                    self.data_frame.ix[similar, 'id_membro'] = self.data_frame.ix[similar, 'id_membro'].apply(lambda x: x | frozenset({row.id_membro}))
            data_frame_to_append.loc[:, 'id_membro'] = data_frame_to_append['id_membro'].apply(lambda x: frozenset({x}))
            self.data_frame = self.data_frame.append(data_frame_to_append[~data_frame_to_append.index.isin(duplicated)], ignore_index=True)
        else:
            self.data_frame = self.data_frame.append(data_frame_to_append, ignore_index=True)

    @staticmethod
    def is_similar(row1, row2):
        # TODO: testar outras similaridades (autores, issn, etc.)
        # TODO: ver se é preciso ignorar quando id_membro é o mesmo
        if similaridade_entre_cadeias(row1.titulo, row2.titulo):
            return True
        return False

    def mark_similar(self):
        self.data_frame['similar'] = self.data_frame.index

        def set_similar(row, ref_row, ref_index):
            if self.is_similar(row, ref_row):
                row.similar = ref_index
            return row

        # Might be better to search for similarity in append (though it'd remain O(n^2))
        for i in self.data_frame.index:
            # self.data_frame.ix[:i-1][self.data_frame.ix[:i-1].apply(lambda x: self.is_similar(x, self.data_frame.ix[i]), axis=1)]
            self.data_frame = self.data_frame.apply(set_similar, axis=1, ref_row=self.data_frame.ix[i], ref_index=i)

    def _get_similar_groups(self):
        if 'similar' not in self.data_frame.columns:
            self.mark_similar()
        grouped = self.data_frame.groupby('similar', as_index=False)
        # grouped.aggregate({'id_membro': lambda x: frozenset(x)})
        # grouped.aggregate(list)
        return grouped

    def _co_authors_list(self):
        # Code below is deprecated; was working when we were using a 'similar' column instead of a frozenset in 'id_membro'
        # grouped = self._get_similar_groups()
        # # self.grouped.filter(lambda x: len(x) > 1)
        # co_authorships = [group for group in grouped.groups.values() if len(group) > 1]
        # co_authors = [list(self.data_frame['id_membro'][co_authors_indexes]) for co_authors_indexes in co_authorships]

        co_authors = list(self.data_frame.ix[self.data_frame['id_membro'].apply(len) > 1, 'id_membro'])
        # FIXME: test method (enable collaboration graph)
        return co_authors

    def co_authorship_adjacency_matrix(self, members_indices):
        if self.adjacency_matrix is None:
            self.adjacency_matrix = create_adjacency_matrix(members_indices, self._co_authors_list())
        return self.adjacency_matrix

    def co_authorship_weighted_matrix(self, members_indices):
        if self.weighted_matrix is None:
            self.weighted_matrix = create_weighted_matrix(members_indices, self._co_authors_list())
        return self.weighted_matrix

    def __len__(self):
        return len(self.data_frame)

    def __iter__(self):
        return self.data_frame.iterrows()

    def pivoted_by(self, column, ascending=True):
        return pd.pivot_table(self.data_frame, index=column).sort_index(ascending=ascending)

    def ordered_dict_by(self, key_by, ascending=True):
        group_dict = {
            key: self.data_frame[self.data_frame[key_by] == key] for key in self.data_frame[key_by].unique()
            }
        return OrderedDict(sorted(group_dict.items(), key=lambda t: t[0], reverse=not ascending))

    def have_qualis(self):
        return 'qualis' in self.data_frame.columns and self.data_frame.qualis.any()

    def filter_by_year(self):
        # FIXME: ver se método é útil
        if not objeto.ano:  # se nao for identificado o ano sempre o mostramos na lista
            objeto.ano = 0
            return 1
        else:
            objeto.ano = int(objeto.ano)
            if objeto.ano < self.items_desde_ano or objeto.ano > self.items_ate_ano:
                return 0
            else:
                retorno = 0
                for per in self.member_timespans:
                    if per[0] <= objeto.ano <= per[1]:
                        retorno = 1
                        break
                return retorno
