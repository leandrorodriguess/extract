#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scriptLattes
~~~~~~~~~~~~

The main entry point for the command line interface.

Invoke as ``scriptlattes`` (if installed)
or ``python -m scriptlattes`` (no install required).

Usage:
  scriptlattes [options] all CONFIG_FILE [--offline]
  scriptlattes [options] download CONFIG_FILE
  scriptlattes [options] extract CONFIG_FILE [--offline]
  scriptlattes process CONFIG_FILE [--offline]
  scriptlattes report CONFIG_FILE [--offline]
  scriptlattes (-h | --help | --version)

Arguments:
  CONFIG_FILE  arquivo de configuração

Options:
  -h --help            show this help message and exit
  --version            show version and exit
  -v --verbose         log debug messages
  -q --quiet           log only warning and error messages

Other:
  --offline            do not try to download data; instead, use persisted data configured in CONFIG_FILE
"""

from __future__ import absolute_import, unicode_literals
import logging
import sys
import pandas

from docopt import docopt
from configobj import ConfigObj
from pathlib import Path

from scriptLattes.log import configure_stream
from fetch.download_html import download_html
from extract.parserLattesHTML import ParserLattesHTML
from extract.parserLattesXML import ParserLattesXML
from persist.cache import cache
from persist.store import Store
from grupo import Grupo
from util import copiarArquivos
import util
from validate import Validator

logger = logging.getLogger(__name__)


# FIXME: incluir comentários abaixo (retirar dos exemplos)
# FIXME: implementar opção de gravar arquivo de configuração padrão

default_configuration = u"""
global-nome_do_grupo = string
global-arquivo_de_entrada = string
global-diretorio_de_saida = string
global-email_do_admin = string
global-idioma = string(default='PT')
global-itens_desde_o_ano = integer(min=1990)
global-itens_ate_o_ano = integer
global-itens_por_pagina = integer(min='1', default='1000')
global-criar_paginas_jsp = boolean(default='não')
global-google_analytics_key = string
global-prefixo = string
global-diretorio_de_armazenamento_de_cvs = string
global-diretorio_de_armazenamento_de_doi = string
global-salvar_informacoes_em_formato_xml = boolean(default='não')

global-identificar_publicacoes_com_qualis = boolean(default='não')
global-usar_cache_qualis = boolean(default='sim')
global-arquivo_areas_qualis = string(default=None)
global-arquivo_qualis_de_congressos = string(default=None)
global-arquivo_qualis_de_periodicos = string(default=None)

relatorio-salvar_publicacoes_em_formato_ris = boolean(default='não')
relatorio-incluir_artigo_em_periodico = boolean(default='sim')
relatorio-incluir_livro_publicado = boolean(default='sim')
relatorio-incluir_capitulo_de_livro_publicado = boolean(default='sim')
relatorio-incluir_texto_em_jornal_de_noticia = boolean(default='sim')
relatorio-incluir_trabalho_completo_em_congresso = boolean(default='sim')
relatorio-incluir_resumo_expandido_em_congresso = boolean(default='sim')
relatorio-incluir_resumo_em_congresso = boolean(default='sim')
relatorio-incluir_artigo_aceito_para_publicacao = boolean(default='sim')
relatorio-incluir_apresentacao_de_trabalho = boolean(default='sim')
relatorio-incluir_outro_tipo_de_producao_bibliografica = boolean(default='sim')

relatorio-incluir_software_com_patente = boolean(default='sim')
relatorio-incluir_software_sem_patente = boolean(default='sim')
relatorio-incluir_produto_tecnologico = boolean(default='sim')
relatorio-incluir_processo_ou_tecnica = boolean(default='sim')
relatorio-incluir_trabalho_tecnico = boolean(default='sim')
relatorio-incluir_outro_tipo_de_producao_tecnica = boolean(default='sim')

relatorio-incluir_patente = boolean(default='sim')
relatorio-incluir_programa_computador = boolean(default='sim')
relatorio-incluir_desenho_industrial = boolean(default='sim')

relatorio-incluir_producao_artistica = boolean(default='sim')

relatorio-mostrar_orientacoes = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_pos_doutorado = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_doutorado = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_mestrado = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_monografia_de_especializacao = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_tcc = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_iniciacao_cientifica = boolean(default='sim')
relatorio-incluir_orientacao_em_andamento_outro_tipo = boolean(default='sim')

relatorio-incluir_orientacao_concluida_pos_doutorado = boolean(default='sim')
relatorio-incluir_orientacao_concluida_doutorado = boolean(default='sim')
relatorio-incluir_orientacao_concluida_mestrado = boolean(default='sim')
relatorio-incluir_orientacao_concluida_monografia_de_especializacao = boolean(default='sim')
relatorio-incluir_orientacao_concluida_tcc = boolean(default='sim')
relatorio-incluir_orientacao_concluida_iniciacao_cientifica = boolean(default='sim')
relatorio-incluir_orientacao_concluida_outro_tipo = boolean(default='sim')

relatorio-incluir_projeto = boolean(default='sim')
relatorio-incluir_premio = boolean(default='sim')
relatorio-incluir_participacao_em_evento = boolean(default='sim')
relatorio-incluir_organizacao_de_evento = boolean(default='sim')
relatorio-incluir_internacionalizacao = boolean(default='não')

grafo-mostrar_grafo_de_colaboracoes = boolean(default='sim')
grafo-mostrar_todos_os_nos_do_grafo = boolean(default='sim')
grafo-considerar_rotulos_dos_membros_do_grupo = boolean(default='sim')
grafo-mostrar_aresta_proporcional_ao_numero_de_colaboracoes = boolean(default='sim')

grafo-incluir_artigo_em_periodico = boolean(default='sim')
grafo-incluir_livro_publicado = boolean(default='sim')
grafo-incluir_capitulo_de_livro_publicado = boolean(default='sim')
grafo-incluir_texto_em_jornal_de_noticia = boolean(default='sim')
grafo-incluir_trabalho_completo_em_congresso = boolean(default='sim')
grafo-incluir_resumo_expandido_em_congresso = boolean(default='sim')
grafo-incluir_resumo_em_congresso = boolean(default='sim')
grafo-incluir_artigo_aceito_para_publicacao = boolean(default='sim')
grafo-incluir_apresentacao_de_trabalho = boolean(default='sim')
grafo-incluir_outro_tipo_de_producao_bibliografica = boolean(default='sim')

grafo-incluir_software_com_patente = boolean(default='sim')
grafo-incluir_software_sem_patente = boolean(default='sim')
grafo-incluir_produto_tecnologico = boolean(default='sim')
grafo-incluir_processo_ou_tecnica = boolean(default='sim')
grafo-incluir_trabalho_tecnico = boolean(default='sim')
grafo-incluir_outro_tipo_de_producao_tecnica = boolean(default='sim')

grafo-incluir_patente = boolean(default='sim')
grafo-incluir_programa_computador = boolean(default='sim')
grafo-incluir_desenho_industrial = boolean(default='sim')

grafo-incluir_producao_artistica = boolean(default='sim')
grafo-incluir_grau_de_colaboracao = boolean(default='não')

mapa-mostrar_mapa_de_geolocalizacao = boolean(default='sim')
mapa-incluir_membros_do_grupo = boolean(default='sim')
mapa-incluir_alunos_de_pos_doutorado = boolean(default='sim')
mapa-incluir_alunos_de_doutorado = boolean(default='sim')
mapa-incluir_alunos_de_mestrado = boolean(default='não')
"""


def load_config(filename):
    spec = default_configuration.split("\n")
    config = ConfigObj(infile=filename, configspec=spec, file_error=False)
    validator = Validator()
    res = config.validate(validator, copy=True)
    return config


def read_list_file(ids_file_path):
    # ids = pandas.read_csv(ids_file_path.open(), sep=None, comment='#', encoding='utf-8', skip_blank_lines=True)
    ids = pandas.read_csv(ids_file_path.open(), sep="[\t,;]", header=None, engine='python',
                          encoding='utf-8', skip_blank_lines=True, converters={0: lambda x: str(x)})
    num_columns = len(ids.columns)
    column_names = ['identificador', 'nome', 'periodo', 'rotulo']
    ids.columns = column_names[:num_columns]
    ids = ids.reindex(columns=column_names, fill_value='')  # Add new columns with empty strings
    return ids


def cli():
    # FIXME: use docopt for command line arguments (or argparse)
    arguments = docopt(__doc__, argv=None, help=True, version='9.0.0', options_first=False)

    """Add some useful functionality here or import from a submodule."""
    # configure root logger to print to STDERR
    if arguments['--verbose']:
        configure_stream(level='DEBUG')
    elif arguments['--quiet']:
        configure_stream(level='WARNING')
    else:
        configure_stream(level='INFO')

    # launch the command line interface
    logger.info("Executando '{}'".format(' '.join(sys.argv)))

    config_file_path = Path(arguments['CONFIG_FILE'])
    if not config_file_path.exists():
        logger.error("Arquivo de configuração '{}' não existe.".format(config_file_path))
        return -1
    config = load_config(str(config_file_path))

    # configure cache
    if 'global-diretorio_de_armazenamento_de_cvs' in config and config.get('global-diretorio_de_armazenamento_de_cvs'):
        cache_path = util.resolve_file_path(config['global-diretorio_de_armazenamento_de_cvs'], config_file_path)
        cache.set_directory(cache_path)
        # FIXME: colocar store como configuração
        store_path = util.resolve_file_path("store.h5", config_file_path)
        store = Store(store_path)

    ids_file_path = util.find_file(Path(config['global-arquivo_de_entrada']), config_file_path)
    if not ids_file_path:
        return -1

    ids = read_list_file(ids_file_path)

    qualis_de_congressos = None
    areas_qualis = None
    if 'global-identificar_publicacoes_com_qualis' in config and config['global-identificar_publicacoes_com_qualis']:
        if config['global-usar_cache_qualis']:
            cache.new_file('qualis.data')
        if config['global-arquivo_qualis_de_congressos']:
            qualis_de_congressos = util.find_file(Path(config['global-arquivo_qualis_de_congressos']), config_file_path)
        if config['global-arquivo_areas_qualis']:
            areas_qualis = util.find_file(Path(config['global-arquivo_areas_qualis']), config_file_path)

    group = Grupo(ids=ids,
                  desde_ano=config['global-itens_desde_o_ano'],
                  ate_ano=config['global-itens_ate_o_ano'],
                  qualis_de_congressos=qualis_de_congressos,
                  areas_qualis=areas_qualis)
    # group.imprimirListaDeParametros()
    # group.imprimirListaDeRotulos()

    cvs_content = {'html': {}, 'xml': {}}
    use_xml = False  # FIXME: definir opção no arquivo de config
    if arguments['download'] or (arguments['extract'] and not arguments['--offline']):
        # obter/carregar
        for id_lattes in ids['identificador']:
            if use_xml:
                # TODO: tentar usar webservice do CNPq
                raise "Download de CVs em XML ainda não implementado."
                # cvs_content['xml'][id_lattes] = cv_xml
            else:  # use html
                cv_html = download_html(id_lattes)
                if cache.directory:
                    id_file = cache.new_file(id_lattes)
                    with id_file.open('w') as f:
                        f.write(cv_html)
                        logger.info("CV '{}' armazenado na cache.".format(id_lattes))
                cvs_content['html'][id_lattes] = cv_html

    if arguments['extract']:
        # extrair/carregar
        if arguments['--offline']:
            if not cache.cache_directory:
                logger.error(
                    "Opção --offline exige que um diretório de cache válido seja usado; verifique seu arquivo de configuração.")
                return -1
            for id_lattes in ids['identificador']:
                if id_lattes == '0000000000000000':
                    # se o codigo for '0000000000000000' então serao considerados dados de pessoa estrangeira - sem Lattes.
                    # sera procurada a coautoria endogena com os outros membro.
                    # para isso é necessario indicar o nome abreviado no arquivo .list
                    # FIXME: verificar se ainda funciona
                    continue
                try:
                    cv_path = (cache.directory / id_lattes).resolve()
                except OSError:
                    logger.error(
                        "O CV {} não existe na cache ('{}'); ignorando.".format(id_lattes, cache.cache_directory))
                    continue

                with cv_path.open() as f:
                    cv_lattes_content = f.read()
                logger.debug("Utilizando CV armazenado no cache: {}.".format(cv_path))

                if use_xml:
                    # TODO: verificar se realmente isto é necessário
                    extended_chars = u''.join(unichr(c) for c in xrange(127, 65536, 1))  # srange(r"[\0x80-\0x7FF]")
                    special_chars = ' -'''
                    cv_lattes_content = cv_lattes_content.decode('iso-8859-1',
                                                                 'replace') + extended_chars + special_chars

                    cvs_content['xml'][id_lattes] = cv_lattes_content
                else:
                    # extended_chars = u''.join(unichr(c) for c in xrange(127, 65536, 1))  # srange(r"[\0x80-\0x7FF]")
                    # special_chars = ' -'''
                    # #cvLattesHTML  = cvLattesHTML.decode('ascii','replace')+extended_chars+special_chars
                    # cvLattesHTML = cvLattesHTML.decode('iso-8859-1', 'replace') + extended_chars + special_chars
                    cvs_content['html'][id_lattes] = cv_lattes_content

        # for id_lattes in ids['identificador']:
        #     if use_xml:
        #         parser = ParserLattesXML(id_lattes, cvs_content['xml'][id_lattes])
        #     else:
        #         parser = ParserLattesHTML(id_lattes, cvs_content['html'][id_lattes])
        if use_xml:
            group.extract_cvs_data(ParserLattesXML, cvs_content['xml'])  # obrigatorio
        else:
            group.extract_cvs_data(ParserLattesHTML, cvs_content['html'])  # obrigatorio

    if arguments['process']:
        # processar/carregar
        pass

    if arguments['report']:
        pass


    # if criarDiretorio('global-diretorio_de_saida')):
    if 'global-diretorio_de_saida' in config:
        group.extract_cvs_data(parser)  # obrigatorio
        group.compilarListasDeItems()  # obrigatorio
        group.identificarQualisEmPublicacoes()  # obrigatorio
        group.calcularInternacionalizacao()  # obrigatorio
        # group.imprimirMatrizesDeFrequencia()

        group.gerarGrafosDeColaboracoes()  # obrigatorio
        # group.gerarGraficosDeBarras() # java charts
        group.gerarMapaDeGeolocalizacao()  # obrigatorio
        group.gerarPaginasWeb()  # obrigatorio
        group.gerarArquivosTemporarios()  # obrigatorio

        # copiar images e css
        copiarArquivos(config['global-diretorio_de_saida'])

        # finalizando o processo
        print('\n\n\n[PARA REFERENCIAR/CITAR ESTE SOFTWARE USE]')
        print('    Jesus P. Mena-Chalco & Roberto M. Cesar-Jr.')
        print('    scriptLattes: An open-source knowledge extraction system from the Lattes Platform.')
        print('    Journal of the Brazilian Computer Society, vol.15, n.4, páginas 31-39, 2009.')
        print('    http://dx.doi.org/10.1007/BF03194511')
        print('\n\nscriptLattes executado!')

        # return 0


if __name__ == '__main__':
    # exit using whatever exit code the CLI returned
    sys.exit(cli())
