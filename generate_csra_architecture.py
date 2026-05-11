from diagrams import Diagram, Cluster, Edge
from diagrams.azure.compute import FunctionApps
from diagrams.azure.storage import BlobStorage
from diagrams.azure.analytics import DataFactories
from diagrams.azure.database import SQLDatabases, CosmosDb
from diagrams.azure.aimachinelearning import CognitiveServices, CognitiveSearch, BotServices
from diagrams.azure.general import Browser
from diagrams.onprem.client import Users

graph_attr = {
    'fontsize':  '13',
    'bgcolor':   'white',
    'pad':       '1.8',
    'splines':   'line',
    'nodesep':   '0.9',
    'ranksep':   '1.8',
}

ZONE  = {'style': 'filled', 'bgcolor': '#E8F4FD', 'pencolor': '#5A9FD4', 'penwidth': '1.5', 'fontsize': '12'}
GREEN = {'style': 'filled', 'bgcolor': '#E8F8EF', 'pencolor': '#2E8B57', 'penwidth': '1.5', 'fontsize': '12'}
EXT   = {'style': 'filled', 'bgcolor': '#F5F0FF', 'pencolor': '#7B2FBE', 'penwidth': '1.5', 'fontsize': '12'}

with Diagram(
    'CSRA Fee Schedule Rule Validation Architecture',
    show=True,
    direction='LR',
    graph_attr=graph_attr,
    filename='csra_architecture_v2',
):
    # -- Sources (rank 0) --
    rules_admin  = Users('Rules Admin')
    state_portal = Browser('State Fee Schedule\nPortal')

    # -- Rules pipeline --
    with Cluster('Rules Ingestion', graph_attr=ZONE):
        rules_blob   = BlobStorage('Rules Excel\n(Uploaded)')
        rules_parser = FunctionApps('Rules Parser\nand SP Generator')

    with Cluster('Rules Repository', graph_attr=ZONE):
        rules_db = SQLDatabases('Rules DB\n(state / primary FS / fee segment)\nRaw Rules and Stored Procs')

    # -- Fee schedule pipeline --
    with Cluster('Fee Schedule Ingestion', graph_attr=ZONE):
        bot  = BotServices('RPA Bot')
        blob = BlobStorage('Raw Files\nBlob Storage')

    with Cluster('Fee Schedule Processing', graph_attr=ZONE):
        adf    = DataFactories('Azure Data Factory')
        fee_db = SQLDatabases('Fee Schedule DB\n(HCPCS / Rates / Comments)')

    # -- AI and retrieval (merge point) --
    with Cluster('AI and Retrieval', graph_attr=ZONE):
        ai_search = CognitiveSearch('Azure AI Search\n(Metadata-Filtered Retrieval)')
        openai    = CognitiveServices('Azure OpenAI GPT-4o')

    # -- Review and output --
    sme = Users('Business SME\nApprove / Decline')

    with Cluster('Updated Rules on Approval', graph_attr=GREEN):
        updated_rules = SQLDatabases('Rules DB\n(Approved Updates Applied)')

    # -- qntxt DB in a separate resource group --
    with Cluster('Separate Resource Group', graph_attr=EXT):
        qntxt_db = CosmosDb('qntxt DB')

    # Rules ingestion pipeline
    rules_admin  >> Edge(label='Upload rules Excel')    >> rules_blob
    rules_blob   >> Edge(label='Parse Excel')           >> rules_parser
    rules_parser >> Edge(label='Store rules and SPs')   >> rules_db

    # Fee schedule ingestion pipeline
    state_portal >> Edge(label='Download Excel / PDF')  >> bot
    bot          >> Edge(label='Upload raw files')      >> blob
    blob         >> Edge(label='Blob trigger')          >> adf
    adf          >> Edge(label='Parse and load')        >> fee_db

    # Both lanes converge at AI Search
    rules_db >> Edge(label='Fetch raw rules and SPs')   >> ai_search
    fee_db   >> Edge(label='Metadata filter', constraint='false') >> ai_search

    # LLM inputs (blue, bold)
    fee_db    >> Edge(xlabel='Comments and Metadata\n(state / primary FS / FS segment)',
                      color='#0078D4', penwidth='2')    >> openai
    ai_search >> Edge(label='Matching rules and SPs\nas LLM context',
                      color='#0078D4', penwidth='2')    >> openai

    # qntxt DB provides context to OpenAI
    qntxt_db  >> Edge(label='Context lookup', color='#7B2FBE', penwidth='2') >> openai

    # Review and approval
    openai >> Edge(label='Suggest updates or\nNo changes needed') >> sme
    sme    >> Edge(label='Approved', style='dashed',
                   color='#2E8B57', penwidth='2')       >> updated_rules
