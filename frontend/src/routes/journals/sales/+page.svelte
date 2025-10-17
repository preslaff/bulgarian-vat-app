<script lang="ts">
  import { onMount } from 'svelte';
  import { FileText, Plus, Eye, ShoppingCart, Save, X, Trash2 } from 'lucide-svelte';
  import { api, VATValidator, type Company, type SalesEntry } from '$lib/api';
  
  let companies: Company[] = [];
  let selectedCompany: Company | null = null;
  let selectedPeriod: string = new Date().toISOString().slice(0, 7).replace('-', '');
  let sales: SalesEntry[] = [];
  let loading = false;
  let error = '';
  let showAddForm = false;
  let saving = false;
  let deletingId: number | null = null;
  
  // VIES validation state for customer VAT
  let customerVatValidation: {
    isValidating: boolean;
    isValid: boolean | null;
    companyName: string | null;
    error: string | null;
  } = {
    isValidating: false,
    isValid: null,
    companyName: null,
    error: null
  };
  
  // Form data for new sales entry
  let newEntry: Partial<SalesEntry> = {
    document_type: 1,
    document_date: new Date().toISOString().split('T')[0],
    tax_base_20: 0,
    vat_20: 0,
    tax_base_0: 0,
    tax_base_exempt: 0,
    total_amount: 0
  };

  onMount(async () => {
    await loadCompanies();
  });

  async function loadCompanies() {
    try {
      companies = await api.listCompanies();
      if (companies.length === 1) {
        selectedCompany = companies[0];
        await loadSales();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането на фирмите';
    }
  }

  async function loadSales() {
    if (!selectedCompany || !selectedPeriod) return;
    
    loading = true;
    error = '';
    
    try {
      sales = await api.getSales(selectedCompany.uic, selectedPeriod);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Грешка при зареждането на продажбите';
      sales = [];
    } finally {
      loading = false;
    }
  }

  // VIES validation function for customer VAT
  async function validateCustomerVAT() {
    if (!newEntry.customer_vat || !selectedCompany) return;
    
    // Reset validation state
    customerVatValidation = {
      isValidating: true,
      isValid: null,
      companyName: null,
      error: null
    };
    
    // Check if it's an EU VAT number (starts with EU country code)
    const euCountries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'];
    const vatNumber = newEntry.customer_vat.trim().toUpperCase();
    
    // Check if VAT number starts with EU country code
    const isEUVat = euCountries.some(country => vatNumber.startsWith(country));
    
    if (!isEUVat) {
      customerVatValidation = {
        isValidating: false,
        isValid: null,
        companyName: null,
        error: 'Не е ЕС ДДС номер - VIES валидация не е необходима'
      };
      return;
    }
    
    try {
      const result = await api.validateFullVAT({
        full_vat_number: vatNumber,
        requester_vat: selectedCompany.vat_number // Use current company's VAT as requester
      });
      
      customerVatValidation = {
        isValidating: false,
        isValid: result.is_valid,
        companyName: result.company_name,
        error: result.is_valid ? null : (result.error_message || 'ДДС номерът не е валиден')
      };
      
      // Auto-fill customer name if validation successful and name is returned
      if (result.is_valid && result.company_name && !newEntry.customer_name) {
        newEntry.customer_name = result.company_name;
      }
      
    } catch (err) {
      customerVatValidation = {
        isValidating: false,
        isValid: false,
        companyName: null,
        error: err instanceof Error ? err.message : 'VIES валидацията се провали'
      };
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

  function getDocumentTypeName(type: number): string {
    switch(type) {
      case 1: return 'Фактура';
      case 2: return 'Дебитно известие';
      case 3: return 'Кредитно известие';
      default: return 'Неизвестен';
    }
  }
  
  function openAddForm() {
    if (!selectedCompany || !selectedPeriod) {
      error = 'Моля изберете фирма и период първо';
      return;
    }
    
    newEntry = {
      period: selectedPeriod,
      document_type: 1,
      document_date: new Date().toISOString().split('T')[0],
      tax_base_20: 0,
      vat_20: 0,
      tax_base_0: 0,
      tax_base_exempt: 0,
      total_amount: 0
    };
    showAddForm = true;
    error = '';
  }
  
  function closeAddForm() {
    showAddForm = false;
    newEntry = {
      document_type: 1,
      document_date: new Date().toISOString().split('T')[0],
      tax_base_20: 0,
      vat_20: 0,
      tax_base_0: 0,
      tax_base_exempt: 0,
      total_amount: 0
    };
    // Reset VIES validation state
    customerVatValidation = {
      isValidating: false,
      isValid: null,
      companyName: null,
      error: null
    };
  }
  
  async function saveSalesEntry() {
    if (!selectedCompany || !newEntry.period) return;
    
    saving = true;
    error = '';
    
    try {
      // Validate required fields
      if (!newEntry.customer_name) {
        throw new Error('Името на клиента е задължително');
      }
      
      if (!newEntry.tax_base_20 && !newEntry.tax_base_0 && !newEntry.tax_base_exempt) {
        throw new Error('Трябва да въведете поне една данъчна основа');
      }
      
      // Auto-calculate VAT if not provided
      if (newEntry.tax_base_20 && !newEntry.vat_20) {
        newEntry.vat_20 = Number((newEntry.tax_base_20 * 0.2).toFixed(2));
      }
      
      // Auto-calculate total
      const taxBase = (newEntry.tax_base_20 || 0) + (newEntry.tax_base_0 || 0) + (newEntry.tax_base_exempt || 0);
      const vat = newEntry.vat_20 || 0;
      newEntry.total_amount = taxBase + vat;
      
      await api.addSalesEntry(selectedCompany.uic, newEntry as SalesEntry);
      await loadSales();
      closeAddForm();
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при запазване');
    } finally {
      saving = false;
    }
  }
  
  // Auto-calculate VAT when tax base changes
  function calculateSalesVAT() {
    if (newEntry.tax_base_20 && newEntry.tax_base_20 > 0) {
      // Always recalculate VAT based on current tax base
      newEntry.vat_20 = Number((newEntry.tax_base_20 * 0.2).toFixed(2));
    } else if (!newEntry.tax_base_20 || newEntry.tax_base_20 === 0) {
      // If tax base is empty or zero, clear VAT
      newEntry.vat_20 = 0;
    }
    
    const taxBase = (newEntry.tax_base_20 || 0) + (newEntry.tax_base_0 || 0) + (newEntry.tax_base_exempt || 0);
    const vat = newEntry.vat_20 || 0;
    newEntry.total_amount = taxBase + vat;
  }
  
  async function deleteSalesEntry(entryId: number, customerName: string) {
    if (!confirm(`Сигурни ли сте, че искате да изтриете записа на ${customerName}?`)) {
      return;
    }
    
    deletingId = entryId;
    error = '';
    
    try {
      await api.deleteSalesEntry(entryId);
      await loadSales(); // Reload the list
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при изтриване');
    } finally {
      deletingId = null;
    }
  }

  $: {
    if (selectedCompany && selectedPeriod) {
      loadSales();
    }
  }
</script>

<svelte:head>
  <title>Дневник за продажбите - VAT System</title>
</svelte:head>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="mb-8">
    <div class="flex justify-between items-center">
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
            <span class="text-gray-900">Дневник за продажбите</span>
          </div>
          <h1 class="text-2xl font-bold text-gray-900">Дневник за продажбите</h1>
          <p class="mt-2 text-gray-600">
            Регистър на изходящи фактури и документи към клиенти
          </p>
        </div>
      </div>
      
      <div class="flex space-x-3">
        <button
          on:click={openAddForm}
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
        >
          <Plus class="h-4 w-4 mr-2" />
          Добави запис
        </button>
        
        <a
          href="/import"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          <FileText class="h-4 w-4 mr-2" />
          Импорт данни
        </a>
      </div>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white shadow rounded-lg p-6 mb-8">
    <h3 class="text-lg font-medium text-gray-900 mb-4">Филтри</h3>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Company Selection -->
      <div>
        <label for="company-select" class="block text-sm font-medium text-gray-700 mb-2">Фирма</label>
        <select
          id="company-select"
          bind:value={selectedCompany}
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
        >
          <option value={null}>Изберете фирма</option>
          {#each companies as company}
            <option value={company}>{company.name} ({company.uic})</option>
          {/each}
        </select>
      </div>

      <!-- Period Selection -->
      <div>
        <label for="period-select" class="block text-sm font-medium text-gray-700 mb-2">Период (YYYYMM)</label>
        <input
          type="text"
          id="period-select"
          bind:value={selectedPeriod}
          placeholder="202401"
          pattern="[0-9]{6}"
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500"
        />
        <p class="mt-1 text-sm text-gray-500">
          Формат: YYYYMM (например: 202401 за януари 2024)
        </p>
      </div>
    </div>
  </div>

  <!-- Add Sales Entry Form -->
  {#if showAddForm}
    <div class="bg-white shadow rounded-lg p-6 mb-8">
      <div class="flex justify-between items-center mb-6">
        <h3 class="text-lg font-medium text-gray-900">Добави нов запис за продажба</h3>
        <button
          on:click={closeAddForm}
          class="text-gray-400 hover:text-gray-600"
        >
          <X class="h-5 w-5" />
        </button>
      </div>
      
      <form on:submit|preventDefault={saveSalesEntry} class="space-y-6">
        <!-- Document Information -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label for="document_type" class="block text-sm font-medium text-gray-700 mb-2">Тип документ</label>
            <select
              id="document_type"
              bind:value={newEntry.document_type}
              required
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value={1}>Фактура</option>
              <option value={2}>Дебитно известие</option>
              <option value={3}>Кредитно известие</option>
            </select>
          </div>
          
          <div>
            <label for="document_number" class="block text-sm font-medium text-gray-700 mb-2">Номер на документ</label>
            <input
              type="text"
              id="document_number"
              bind:value={newEntry.document_number}
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="2024001"
            />
          </div>
          
          <div>
            <label for="document_date" class="block text-sm font-medium text-gray-700 mb-2">Дата на документ</label>
            <input
              type="date"
              id="document_date"
              bind:value={newEntry.document_date}
              required
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <!-- Customer Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label for="customer_name" class="block text-sm font-medium text-gray-700 mb-2">Име на клиент *</label>
            <input
              type="text"
              id="customer_name"
              bind:value={newEntry.customer_name}
              required
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="КЛИЕНТ ООД"
            />
          </div>
          
          <div>
            <label for="customer_vat" class="block text-sm font-medium text-gray-700 mb-2">ДДС номер на клиент</label>
            <div class="relative">
              <input
                type="text"
                id="customer_vat"
                bind:value={newEntry.customer_vat}
                on:blur={validateCustomerVAT}
                class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
                placeholder="BG123456789 или DE123456789"
              />
              
              <!-- VIES Validation Status Icon -->
              {#if customerVatValidation.isValidating}
                <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" title="Проверява се в VIES системата..."></div>
                </div>
              {:else if customerVatValidation.isValid === true}
                <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                  </svg>
                </div>
              {:else if customerVatValidation.isValid === false}
                <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                  </svg>
                </div>
              {/if}
            </div>
            
            <!-- VIES Validation Result Messages -->
            {#if customerVatValidation.isValidating}
              <div class="mt-2 text-sm text-blue-600 bg-blue-50 rounded p-2 flex items-center">
                <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-2"></div>
                🌐 Проверява се валидността на ДДС номера в VIES системата на ЕС...
              </div>
            {:else if customerVatValidation.companyName}
              <div class="mt-2 text-sm text-green-600 bg-green-50 rounded p-2">
                ✓ Валиден ЕС ДДС номер: <strong>{customerVatValidation.companyName}</strong>
              </div>
            {/if}
            
            {#if customerVatValidation.error && customerVatValidation.isValid !== null}
              <div class="mt-2 text-sm text-amber-600 bg-amber-50 rounded p-2">
                ⓘ {customerVatValidation.error}
              </div>
            {/if}
          </div>
        </div>
        
        <!-- VAT Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label for="tax_base_20" class="block text-sm font-medium text-gray-700 mb-2">Данъчна основа 20% (лв.)</label>
            <input
              type="number"
              id="tax_base_20"
              bind:value={newEntry.tax_base_20}
              on:input={calculateSalesVAT}
              step="0.01"
              min="0"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="100.00"
            />
          </div>
          
          <div>
            <label for="vat_20" class="block text-sm font-medium text-gray-700 mb-2">ДДС 20% (лв.)</label>
            <input
              type="number"
              id="vat_20"
              bind:value={newEntry.vat_20}
              step="0.01"
              min="0"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="20.00"
            />
          </div>
        </div>
        
        <!-- Other VAT Bases -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label for="tax_base_0" class="block text-sm font-medium text-gray-700 mb-2">Данъчна основа 0% (лв.)</label>
            <input
              type="number"
              id="tax_base_0"
              bind:value={newEntry.tax_base_0}
              on:input={calculateSalesVAT}
              step="0.01"
              min="0"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="0.00"
            />
          </div>
          
          <div>
            <label for="tax_base_exempt" class="block text-sm font-medium text-gray-700 mb-2">Освободени доставки (лв.)</label>
            <input
              type="number"
              id="tax_base_exempt"
              bind:value={newEntry.tax_base_exempt}
              on:input={calculateSalesVAT}
              step="0.01"
              min="0"
              class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="0.00"
            />
          </div>
        </div>
        
        <!-- Total Amount (calculated) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label for="total_amount" class="block text-sm font-medium text-gray-700 mb-2">Обща сума (лв.)</label>
            <input
              type="number"
              id="total_amount"
              bind:value={newEntry.total_amount}
              step="0.01"
              min="0"
              readonly
              class="block w-full rounded-md border-gray-300 bg-gray-50 shadow-sm"
              placeholder="Изчислява се автоматично"
            />
          </div>
        </div>
        
        <!-- Notes -->
        <div>
          <label for="notes" class="block text-sm font-medium text-gray-700 mb-2">Бележки</label>
          <textarea
            id="notes"
            bind:value={newEntry.notes}
            rows="3"
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            placeholder="Допълнителна информация..."
          ></textarea>
        </div>
        
        <!-- Form Actions -->
        <div class="flex justify-end space-x-4">
          <button
            type="button"
            on:click={closeAddForm}
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            Отказ
          </button>
          
          <button
            type="submit"
            disabled={saving || customerVatValidation.isValidating}
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 disabled:opacity-50"
          >
            {#if saving}
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Запазва...
            {:else}
              <Save class="h-4 w-4 mr-2" />
              Запази запис
            {/if}
          </button>
        </div>
      </form>
    </div>
  {/if}

  <!-- Error Message -->
  {#if error}
    <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="flex items-center">
        <div class="text-red-500 mr-2">⚠️</div>
        <p class="text-red-700">{error}</p>
      </div>
    </div>
  {/if}

  <!-- Loading -->
  {#if loading}
    <div class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
      <p class="mt-2 text-gray-600">Зареждане на данни...</p>
    </div>
  {/if}

  <!-- Sales Table -->
  {#if !loading && sales.length > 0}
    <div class="bg-white shadow rounded-lg overflow-hidden mb-8">
      <div class="px-6 py-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          Продажби за {selectedPeriod} - {sales.length} записа
        </h3>
        
        <!-- Summary -->
        <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-green-50 rounded-lg p-4">
            <div class="text-2xl font-bold text-green-900">
              {formatCurrency(sales.reduce((sum, s) => sum + (s.tax_base || 0), 0))}
            </div>
            <div class="text-sm text-green-600">Обща данъчна основа</div>
          </div>
          
          <div class="bg-blue-50 rounded-lg p-4">
            <div class="text-2xl font-bold text-blue-900">
              {formatCurrency(sales.reduce((sum, s) => sum + (s.vat_amount || 0), 0))}
            </div>
            <div class="text-sm text-blue-600">Общо ДДС</div>
          </div>
          
          <div class="bg-purple-50 rounded-lg p-4">
            <div class="text-2xl font-bold text-purple-900">
              {formatCurrency(sales.reduce((sum, s) => sum + (s.total_amount || 0), 0))}
            </div>
            <div class="text-sm text-purple-600">Обща стойност</div>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Документ</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Клиент</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Данъчна основа</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">ДДС</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Обща сума</th>
              <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Действия</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each sales as sale}
              <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">{sale.document_number}</div>
                  <div class="text-sm text-gray-500">
                    {getDocumentTypeName(sale.document_type)} • {formatDate(sale.document_date)}
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="text-sm text-gray-900">{sale.customer_name}</div>
                  <div class="text-sm text-gray-500">
                    {#if sale.customer_vat_number}
                      {sale.customer_vat_number}
                    {:else}
                      {sale.customer_uic}
                    {/if}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {formatCurrency(sale.tax_base || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                  {formatCurrency(sale.vat_amount || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                  {formatCurrency(sale.total_amount || 0)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                  <div class="flex justify-center space-x-2">
                    <button
                      class="text-blue-600 hover:text-blue-900"
                      title="Преглед"
                    >
                      <Eye class="h-4 w-4" />
                    </button>
                    
                    <button
                      on:click={() => deleteSalesEntry(sale.id, sale.customer_name)}
                      disabled={deletingId === sale.id}
                      class="text-red-600 hover:text-red-900 disabled:opacity-50"
                      title="Изтрий запис"
                    >
                      {#if deletingId === sale.id}
                        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600"></div>
                      {:else}
                        <Trash2 class="h-4 w-4" />
                      {/if}
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {:else if !loading}
    <div class="bg-white shadow rounded-lg p-12 text-center">
      <ShoppingCart class="h-16 w-16 text-gray-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-gray-900 mb-2">Няма записи</h3>
      <p class="text-gray-600 mb-6">
        Не са намерени продажби за избраната фирма и период.
      </p>
      <a
        href="/import"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
      >
        <Plus class="h-4 w-4 mr-2" />
        Импортирай данни
      </a>
    </div>
  {/if}

  <!-- Instructions -->
  <div class="bg-gray-50 rounded-lg p-6">
    <h3 class="text-lg font-medium text-gray-900 mb-4">За дневника за продажбите</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <h4 class="font-medium text-gray-900 mb-2">Какво включва</h4>
        <ul class="text-sm text-gray-600 space-y-1">
          <li>• Изходящи фактури към клиенти</li>
          <li>• Документи за продажба на услуги</li>
          <li>• Кредитни известия</li>
          <li>• Експортни документи</li>
        </ul>
      </div>
      <div>
        <h4 class="font-medium text-gray-900 mb-2">Важни бележки</h4>
        <ul class="text-sm text-gray-600 space-y-1">
          <li>• Данните се групират по период (месец)</li>
          <li>• Автоматично изчисление на ДДС суми</li>
          <li>• Валидация на ЕИК и ДДС номера</li>
          <li>• Експорт за НАП декларации</li>
        </ul>
      </div>
    </div>
  </div>
</div>
