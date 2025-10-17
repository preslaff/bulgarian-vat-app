<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { ArrowLeft, Calendar, FileText, Download, TrendingUp, Globe } from 'lucide-svelte';
  import { api, type Company, type CompanyVATSummary, type CompanyMonthlyBreakdown, type CompanyEUTransactions } from '$lib/api';
  
  let companyId: string;
  let company: Company | null = null;
  let loading = false;
  let error = '';
  
  // Report data
  let vatSummary: CompanyVATSummary | null = null;
  let monthlyBreakdown: CompanyMonthlyBreakdown | null = null;
  let euTransactions: CompanyEUTransactions | null = null;
  
  // Date filters
  let startDate = new Date();
  startDate.setMonth(startDate.getMonth() - 1); // Default to last month
  let endDate = new Date();
  let selectedYear = new Date().getFullYear();
  
  // Format dates for input fields
  let startDateStr = startDate.toISOString().split('T')[0];
  let endDateStr = endDate.toISOString().split('T')[0];
  
  onMount(async () => {
    companyId = $page.params.id;
    await loadCompany();
    await loadReports();
  });

  async function loadCompany() {
    try {
      const companies = await api.listCompanies();
      company = companies.find(c => c.id.toString() === companyId) || null;
      if (!company) {
        error = 'Фирмата не е намерена';
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането';
    }
  }

  async function loadReports() {
    if (!company) return;
    
    loading = true;
    error = '';
    
    try {
      // Load all reports in parallel
      const [summary, breakdown, eu] = await Promise.all([
        api.getCompanyVATSummary(company.id, startDateStr, endDateStr),
        api.getCompanyMonthlyBreakdown(company.id, selectedYear),
        api.getCompanyEUTransactions(company.id, startDateStr, endDateStr)
      ]);
      
      vatSummary = summary;
      monthlyBreakdown = breakdown;
      euTransactions = eu;
      
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането на отчетите';
    } finally {
      loading = false;
    }
  }

  function handleDateChange() {
    startDateStr = new Date(startDateStr).toISOString().split('T')[0];
    endDateStr = new Date(endDateStr).toISOString().split('T')[0];
    loadReports();
  }

  function handleYearChange() {
    loadReports();
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('bg-BG', {
      style: 'currency',
      currency: 'BGN',
      minimumFractionDigits: 2
    }).format(amount);
  }

  function formatNumber(num: number): string {
    return new Intl.NumberFormat('bg-BG').format(num);
  }

  function exportToCSV(data: any[], filename: string) {
    // Simple CSV export functionality
    console.log('Exporting to CSV:', filename, data);
    // TODO: Implement actual CSV export
  }
</script>

<svelte:head>
  <title>Справки и отчети - {company?.name || 'Фирма'} - VAT System</title>
</svelte:head>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <div class="flex items-center">
      <a 
        href="/" 
        class="mr-4 p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        title="Към началната страница"
      >
        <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      </a>
      <div>
        <div class="flex items-center text-sm text-gray-500 mb-1">
          <a href="/" class="hover:text-gray-700">Начало</a>
          <span class="mx-2">›</span>
          <a href="/companies" class="hover:text-gray-700">Служебни функции</a>
          <span class="mx-2">›</span>
          <span class="text-gray-900">Справки и отчети</span>
        </div>
        <h1 class="text-3xl font-bold text-gray-900">Справки и отчети</h1>
        {#if company}
          <p class="mt-2 text-lg text-gray-600">
            {company.name} • ЕИК: {company.uic} • ДДС: {company.vat_number}
          </p>
        {/if}
      </div>
    </div>
  </div>

  {#if error}
    <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-red-700">{error}</p>
    </div>
  {/if}

  {#if company}
    <!-- Date Filters -->
    <div class="mb-8 bg-white rounded-lg shadow-sm p-6">
      <div class="flex items-center mb-4">
        <Calendar class="h-5 w-5 text-gray-400 mr-2" />
        <h3 class="text-lg font-medium text-gray-900">Филтри за период</h3>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label for="start-date" class="block text-sm font-medium text-gray-700 mb-2">От дата</label>
          <input
            id="start-date"
            type="date"
            bind:value={startDateStr}
            on:change={handleDateChange}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
        <div>
          <label for="end-date" class="block text-sm font-medium text-gray-700 mb-2">До дата</label>
          <input
            id="end-date"
            type="date"
            bind:value={endDateStr}
            on:change={handleDateChange}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          />
        </div>
        <div>
          <label for="year-select" class="block text-sm font-medium text-gray-700 mb-2">Година (месечна разбивка)</label>
          <select
            id="year-select"
            bind:value={selectedYear}
            on:change={handleYearChange}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            {#each Array.from({length: 5}, (_, i) => new Date().getFullYear() - i) as year}
              <option value={year}>{year}</option>
            {/each}
          </select>
        </div>
        <div class="flex items-end">
          <button
            on:click={loadReports}
            disabled={loading}
            class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Зареждане...' : 'Обнови отчетите'}
          </button>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-4 text-gray-600">Зареждане на отчети...</p>
      </div>
    {:else}
      <!-- Reports Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        <!-- VAT Summary Report -->
        {#if vatSummary}
          <div class="bg-white rounded-lg shadow-sm">
            <div class="px-6 py-4 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <FileText class="h-5 w-5 text-blue-600 mr-2" />
                  <h3 class="text-lg font-medium text-gray-900">ДДС Сводка</h3>
                </div>
                <button
                  on:click={() => exportToCSV([vatSummary], 'vat-summary')}
                  class="text-gray-400 hover:text-gray-600"
                >
                  <Download class="h-4 w-4" />
                </button>
              </div>
              <p class="text-sm text-gray-500">
                {vatSummary.period.start_date} - {vatSummary.period.end_date}
              </p>
            </div>
            
            <div class="p-6">
              <!-- Summary cards -->
              <div class="grid grid-cols-2 gap-4 mb-6">
                <div class="bg-green-50 p-4 rounded-lg">
                  <p class="text-sm font-medium text-green-800">Продажби</p>
                  <p class="text-2xl font-bold text-green-900">{formatCurrency(vatSummary.summary.sales.total_amount)}</p>
                  <p class="text-sm text-green-600">ДДС: {formatCurrency(vatSummary.summary.sales.total_vat)}</p>
                  <p class="text-xs text-green-500">{vatSummary.summary.sales.count} документа</p>
                </div>
                
                <div class="bg-red-50 p-4 rounded-lg">
                  <p class="text-sm font-medium text-red-800">Покупки</p>
                  <p class="text-2xl font-bold text-red-900">{formatCurrency(vatSummary.summary.purchases.total_amount)}</p>
                  <p class="text-sm text-red-600">ДДС: {formatCurrency(vatSummary.summary.purchases.total_vat)}</p>
                  <p class="text-xs text-red-500">{vatSummary.summary.purchases.count} документа</p>
                </div>
              </div>
              
              <!-- Net VAT Position -->
              <div class="bg-blue-50 p-4 rounded-lg">
                <p class="text-sm font-medium text-blue-800">Нетна ДДС позиция</p>
                <p class="text-2xl font-bold {vatSummary.summary.net_vat_position >= 0 ? 'text-green-900' : 'text-red-900'}">
                  {formatCurrency(vatSummary.summary.net_vat_position)}
                </p>
                <p class="text-xs text-blue-600">
                  {vatSummary.summary.net_vat_position >= 0 ? 'За доплащане' : 'За възстановяване'}
                </p>
              </div>
            </div>
          </div>
        {/if}

        <!-- Monthly Breakdown -->
        {#if monthlyBreakdown}
          <div class="bg-white rounded-lg shadow-sm">
            <div class="px-6 py-4 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <TrendingUp class="h-5 w-5 text-purple-600 mr-2" />
                  <h3 class="text-lg font-medium text-gray-900">Месечна разбивка {monthlyBreakdown.year}</h3>
                </div>
                <button
                  on:click={() => exportToCSV(monthlyBreakdown.months, 'monthly-breakdown')}
                  class="text-gray-400 hover:text-gray-600"
                >
                  <Download class="h-4 w-4" />
                </button>
              </div>
            </div>
            
            <div class="p-6">
              <div class="space-y-3">
                {#each monthlyBreakdown.months as month}
                  <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <p class="font-medium text-gray-900">{month.month_name}</p>
                      <p class="text-sm text-gray-500">
                        {month.purchases.count + month.sales.count} документа
                      </p>
                    </div>
                    <div class="text-right">
                      <p class="text-sm text-gray-600">
                        Продажби: {formatCurrency(month.sales.amount)}
                      </p>
                      <p class="text-sm text-gray-600">
                        Покупки: {formatCurrency(month.purchases.amount)}
                      </p>
                      <p class="font-medium {month.net_vat >= 0 ? 'text-green-600' : 'text-red-600'}">
                        ДДС: {formatCurrency(month.net_vat)}
                      </p>
                    </div>
                  </div>
                {/each}
              </div>
              
              <!-- Yearly totals -->
              <div class="mt-6 pt-4 border-t border-gray-200">
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <p class="text-sm text-gray-600">Общо продажби</p>
                    <p class="font-bold text-green-600">{formatCurrency(monthlyBreakdown.totals.sales.amount)}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-600">Общо покупки</p>
                    <p class="font-bold text-red-600">{formatCurrency(monthlyBreakdown.totals.purchases.amount)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- EU Transactions -->
        {#if euTransactions && (euTransactions.eu_transactions.purchases.length > 0 || euTransactions.eu_transactions.sales.length > 0)}
          <div class="lg:col-span-2 bg-white rounded-lg shadow-sm">
            <div class="px-6 py-4 border-b border-gray-200">
              <div class="flex items-center justify-between">
                <div class="flex items-center">
                  <Globe class="h-5 w-5 text-indigo-600 mr-2" />
                  <h3 class="text-lg font-medium text-gray-900">ЕС транзакции (VIES)</h3>
                </div>
                <button
                  on:click={() => exportToCSV([...euTransactions.eu_transactions.purchases, ...euTransactions.eu_transactions.sales], 'eu-transactions')}
                  class="text-gray-400 hover:text-gray-600"
                >
                  <Download class="h-4 w-4" />
                </button>
              </div>
              <p class="text-sm text-gray-500">
                {euTransactions.period.start_date} - {euTransactions.period.end_date}
              </p>
            </div>
            
            <div class="p-6">
              <!-- Country Summary -->
              {#if Object.keys(euTransactions.eu_transactions.country_summary).length > 0}
                <div class="mb-6">
                  <h4 class="text-md font-medium text-gray-900 mb-3">Разбивка по държави</h4>
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {#each Object.entries(euTransactions.eu_transactions.country_summary) as [country, data]}
                      <div class="bg-gray-50 p-3 rounded">
                        <p class="font-medium text-gray-900">{country}</p>
                        <p class="text-sm text-green-600">
                          Продажби: {formatCurrency(data.supplies.amount)} ({data.supplies.count})
                        </p>
                        <p class="text-sm text-red-600">
                          Покупки: {formatCurrency(data.acquisitions.amount)} ({data.acquisitions.count})
                        </p>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Transactions Tables -->
              <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <!-- EU Purchases -->
                {#if euTransactions.eu_transactions.purchases.length > 0}
                  <div>
                    <h4 class="text-md font-medium text-gray-900 mb-3">
                      ЕС Покупки ({euTransactions.eu_transactions.purchases.length})
                    </h4>
                    <div class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                          <tr>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Доставчик</th>
                            <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Сума</th>
                            <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Държава</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                          {#each euTransactions.eu_transactions.purchases.slice(0, 10) as purchase}
                            <tr>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                                {new Date(purchase.document_date).toLocaleDateString('bg-BG')}
                              </td>
                              <td class="px-3 py-2 text-sm text-gray-900">
                                <div class="truncate max-w-32">
                                  {purchase.supplier_name}
                                </div>
                                <div class="text-xs text-gray-500">{purchase.supplier_vat_number}</div>
                              </td>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 text-right">
                                {formatCurrency(purchase.amount)}
                              </td>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-center">
                                <span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                                  {purchase.country}
                                </span>
                              </td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                    </div>
                  </div>
                {/if}

                <!-- EU Sales -->
                {#if euTransactions.eu_transactions.sales.length > 0}
                  <div>
                    <h4 class="text-md font-medium text-gray-900 mb-3">
                      ЕС Продажби ({euTransactions.eu_transactions.sales.length})
                    </h4>
                    <div class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                          <tr>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Дата</th>
                            <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Клиент</th>
                            <th class="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Сума</th>
                            <th class="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Държава</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                          {#each euTransactions.eu_transactions.sales.slice(0, 10) as sale}
                            <tr>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                                {new Date(sale.document_date).toLocaleDateString('bg-BG')}
                              </td>
                              <td class="px-3 py-2 text-sm text-gray-900">
                                <div class="truncate max-w-32">
                                  {sale.customer_name}
                                </div>
                                <div class="text-xs text-gray-500">{sale.customer_vat_number}</div>
                              </td>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900 text-right">
                                {formatCurrency(sale.amount)}
                              </td>
                              <td class="px-3 py-2 whitespace-nowrap text-sm text-center">
                                <span class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                                  {sale.country}
                                </span>
                              </td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                    </div>
                  </div>
                {/if}
              </div>
            </div>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>