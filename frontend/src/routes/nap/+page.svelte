<script lang="ts">
  import { onMount } from 'svelte';
  import { Send, CreditCard, FileText, CheckCircle, Clock, AlertCircle, Building2, ExternalLink } from 'lucide-svelte';
  import { api, type Company, type VATDeclaration } from '$lib/api';
  
  let companies: Company[] = [];
  let declarations: VATDeclaration[] = [];
  let loading = true;
  let error = '';

  const paymentMethods = [
    {
      name: 'Банков превод',
      description: 'Плащане чрез банкова сметка',
      icon: CreditCard,
      available: true
    },
    {
      name: 'Онлайн плащане',  
      description: 'Директно плащане с карта',
      icon: CreditCard,
      available: false
    },
    {
      name: 'НАП Портал',
      description: 'Официален портал на НАП',
      icon: ExternalLink,
      available: true,
      url: 'https://portal.nap.bg'
    }
  ];

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    try {
      loading = true;
      companies = await api.listCompanies();
      // TODO: Load recent declarations for all companies
      declarations = [];
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
    } finally {
      loading = false;
    }
  }

  function getStatusInfo(status: string) {
    switch (status) {
      case 'DRAFT':
        return { label: 'Чернова', color: 'text-gray-600 bg-gray-100', icon: FileText };
      case 'SUBMITTED':
        return { label: 'Подадена', color: 'text-blue-600 bg-blue-100', icon: Send };
      case 'PAID':
        return { label: 'Платена', color: 'text-green-600 bg-green-100', icon: CheckCircle };
      default:
        return { label: status, color: 'text-gray-600 bg-gray-100', icon: Clock };
    }
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
    }).format(amount);
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('bg-BG');
  }

  async function payDeclaration(declarationId: number) {
    // TODO: Implement payment flow
    alert('Функционалността за плащане е в процес на разработка');
  }

  function openNAPPortal() {
    window.open('https://portal.nap.bg', '_blank');
  }
</script>

<svelte:head>
  <title>НАП - Подаване и плащания - VAT System</title>
</svelte:head>

<div class="max-w-6xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-gray-900">НАП - Подаване и плащания</h1>
    <p class="mt-2 text-gray-600">
      Управление на подадени декларации и плащания към Национална агенция за приходите
    </p>
  </div>

  <!-- Error Message -->
  {#if error}
    <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="flex items-center">
        <AlertCircle class="h-5 w-5 text-red-500 mr-2" />
        <p class="text-red-700">{error}</p>
      </div>
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Зареждане...</p>
    </div>
  {:else}
    <!-- Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
      {#each paymentMethods as method}
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center mb-4">
            <svelte:component this={method.icon} class="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <h3 class="text-lg font-medium text-gray-900">{method.name}</h3>
              <p class="text-sm text-gray-500">{method.description}</p>
            </div>
          </div>
          
          {#if method.available}
            <button
              on:click={method.url ? openNAPPortal : undefined}
              class="w-full px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              {method.url ? 'Отвори портал' : 'Използвай'}
            </button>
          {:else}
            <button
              disabled
              class="w-full px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-500 bg-gray-100"
            >
              Скоро достъпно
            </button>
          {/if}
        </div>
      {/each}
    </div>

    <!-- Submitted Declarations -->
    <div class="bg-white rounded-lg shadow-sm mb-8">
      <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Подадени декларации</h3>
      </div>
      
      <div class="p-6">
        {#if declarations.length === 0}
          <div class="text-center py-8">
            <Send class="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">Няма подадени декларации</h3>
            <p class="text-gray-500 mb-4">
              Подадените ДДС декларации ще се показват тук
            </p>
            <a
              href="/declarations"
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <FileText class="h-4 w-4 mr-2" />
              Създай декларация
            </a>
          </div>
        {:else}
          <div class="space-y-4">
            {#each declarations as declaration}
              {@const status = getStatusInfo(declaration.status)}
              <div class="border border-gray-200 rounded-lg p-4">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="font-medium text-gray-900">
                      Декларация за период {declaration.period}
                    </h4>
                    <p class="text-sm text-gray-500 mt-1">
                      Подадена: {declaration.submission_date ? formatDate(declaration.submission_date) : 'Неподадена'}
                    </p>
                    {#if declaration.nap_submission_id}
                      <p class="text-xs text-gray-400">
                        Референтен номер НАП: {declaration.nap_submission_id}
                      </p>
                    {/if}
                  </div>
                  
                  <div class="flex items-center space-x-4">
                    <div class="flex items-center">
                      <svelte:component this={status.icon} class="h-4 w-4 mr-1" />
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {status.color}">
                        {status.label}
                      </span>
                    </div>
                    
                    {#if declaration.payment_due > 0 && declaration.status === 'SUBMITTED'}
                      <button
                        on:click={() => payDeclaration(declaration.id)}
                        class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-white bg-orange-600 hover:bg-orange-700"
                      >
                        <CreditCard class="h-3 w-3 mr-1" />
                        Плати {formatCurrency(declaration.payment_due)}
                      </button>
                    {/if}
                  </div>
                </div>
                
                {#if declaration.payment_deadline}
                  <div class="mt-3 p-3 bg-orange-50 border border-orange-200 rounded">
                    <div class="flex items-center">
                      <Clock class="h-4 w-4 text-orange-500 mr-2" />
                      <span class="text-sm text-orange-800">
                        Срок за плащане: {formatDate(declaration.payment_deadline)}
                      </span>
                    </div>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Companies Status -->
    <div class="bg-white rounded-lg shadow-sm">
      <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">Статус на фирмите</h3>
      </div>
      
      <div class="p-6">
        {#if companies.length === 0}
          <div class="text-center py-8">
            <Building2 class="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-gray-900">Няма регистрирани фирми</h3>
            <p class="text-gray-500 mb-4">
              Регистрирайте фирма за да започнете работа с НАП
            </p>
            <a
              href="/companies/new"
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <Building2 class="h-4 w-4 mr-2" />
              Регистрирай фирма
            </a>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each companies.filter(c => c.is_active) as company}
              <div class="border border-gray-200 rounded-lg p-4">
                <h4 class="font-medium text-gray-900">{company.name}</h4>
                <div class="mt-2 space-y-1">
                  <p class="text-sm text-gray-600">УИК: {company.uic}</p>
                  <p class="text-sm text-gray-600">ДДС: {company.vat_number}</p>
                  <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Активна
                  </span>
                </div>
                
                <div class="mt-4 flex space-x-2">
                  <a
                    href="/declarations?company={company.id}"
                    class="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
                  >
                    Декларации
                  </a>
                  <a
                    href="/journals?company={company.id}"
                    class="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded hover:bg-purple-200"
                  >
                    Дневници
                  </a>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Information Section -->
    <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
      <h3 class="text-lg font-medium text-blue-900 mb-4">Информация за НАП</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="font-medium text-blue-900 mb-2">Срокове за подаване</h4>
          <ul class="text-sm text-blue-800 space-y-1">
            <li>• Месечна ДДС декларация: до 14-то число на следващия месец</li>
            <li>• Квартална ДДС декларация: до 31 януари за Q4</li>
            <li>• VIES декларация: до 25-то число на следващия месец</li>
            <li>• Закъснение: глоба от 50 до 1500 лева</li>
          </ul>
        </div>
        <div>
          <h4 class="font-medium text-blue-900 mb-2">Начини за плащане</h4>
          <ul class="text-sm text-blue-800 space-y-1">
            <li>• Банков превод към НАП</li>
            <li>• Плащане в банките партньори</li>
            <li>• Онлайн чрез НАП портал</li>
            <li>• При закъснение: лихви от 0.1% на ден</li>
          </ul>
        </div>
      </div>
      
      <div class="mt-6 p-4 bg-white rounded border">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-medium text-blue-900">НАП Онлайн портал</h4>
            <p class="text-sm text-blue-700">Достъп до всички услуги на НАП</p>
          </div>
          <button
            on:click={openNAPPortal}
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <ExternalLink class="h-4 w-4 mr-2" />
            Отвори portal.nap.bg
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>