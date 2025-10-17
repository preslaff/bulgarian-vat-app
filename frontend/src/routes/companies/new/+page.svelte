<script lang="ts">
  import { goto } from '$app/navigation';
  import { Building2, Save, ArrowLeft, AlertCircle } from 'lucide-svelte';
  import { api, VATValidator, type CompanyCreate } from '$lib/api';
  
  let company: CompanyCreate = {
    name: '',
    uic: '',
    vat_number: '',
    address: '',
    is_active: true
  };
  
  let loading = false;
  let error = '';
  let validationErrors: Record<string, string> = {};
  
  // VIES validation state
  let viesValidation: {
    isValidating: boolean;
    isValid: boolean | null;
    companyName: string | null;
    companyAddress: string | null;
    error: string | null;
  } = {
    isValidating: false,
    isValid: null,
    companyName: null,
    companyAddress: null,
    error: null
  };

  function validateForm(): boolean {
    validationErrors = {};
    
    if (!company.name.trim()) {
      // If VIES validation is successful and has company name, it's okay to be empty (will be auto-filled)
      if (!(viesValidation.isValid && viesValidation.companyName)) {
        validationErrors.name = 'Името на фирмата е задължително';
      }
    }
    
    if (!company.uic.trim()) {
      // UIC is only required for Bulgarian companies
      const vatNumber = company.vat_number.trim().toUpperCase();
      if (vatNumber.startsWith('BG')) {
        validationErrors.uic = 'ЕИК е задължителен за български фирми';
      }
    } else if (!VATValidator.validateUIC(company.uic)) {
      validationErrors.uic = 'Невалиден ЕИК';
    }
    
    if (!company.vat_number.trim()) {
      validationErrors.vat_number = 'ДДС номерът е задължителен';
    } else {
      const vatNumber = company.vat_number.trim().toUpperCase();
      const euCountries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'];
      const isValidFormat = euCountries.some(country => vatNumber.startsWith(country)) && vatNumber.length >= 8;
      
      if (!isValidFormat) {
        validationErrors.vat_number = 'Невалиден формат на ДДС номер (трябва да започва с код на ЕС държава)';
      }
    }
    
    if (!company.address.trim()) {
      // If VIES validation is successful and has address, it's okay to be empty (will be auto-filled)
      if (!(viesValidation.isValid && viesValidation.companyAddress)) {
        validationErrors.address = 'Адресът е задължителен';
      }
    }
    
    return Object.keys(validationErrors).length === 0;
  }

  async function handleSubmit() {
    // Wait for any pending VIES validation to complete
    if (viesValidation.isValidating) {
      return; // Don't submit while validation is in progress
    }
    
    // Auto-fill from VIES data if available and fields are empty
    if (viesValidation.isValid) {
      if (viesValidation.companyName && !company.name.trim()) {
        company.name = viesValidation.companyName;
      }
      if (viesValidation.companyAddress && !company.address.trim()) {
        company.address = viesValidation.companyAddress;
      }
    }
    
    if (!validateForm()) return;
    
    loading = true;
    error = '';
    
    try {
      await api.createCompany(company);
      goto('/companies');
    } catch (e) {
      error = VATValidator.getErrorMessage(e instanceof Error ? e.message : 'Грешка при създаване');
    } finally {
      loading = false;
    }
  }

  function handleUICChange() {
    // Auto-generate VAT number when UIC changes
    if (company.uic && VATValidator.validateUIC(company.uic)) {
      company.vat_number = `BG${company.uic}`;
    }
  }

  // VIES validation function for company creation
  async function validateCompanyVAT() {
    if (!company.vat_number) return;
    
    // Reset validation state
    viesValidation = {
      isValidating: true,
      isValid: null,
      companyName: null,
      companyAddress: null,
      error: null
    };
    
    // Check if it's an EU VAT number (starts with EU country code)
    const euCountries = ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'];
    const vatNumber = company.vat_number.trim().toUpperCase();
    
    // Check if VAT number starts with EU country code
    const isEUVat = euCountries.some(country => vatNumber.startsWith(country));
    
    if (!isEUVat) {
      viesValidation = {
        isValidating: false,
        isValid: null,
        companyName: null,
        companyAddress: null,
        error: 'Не е ЕС ДДС номер - VIES валидация не е налична'
      };
      return;
    }
    
    try {
      // For company creation, we don't have a requester_vat yet, so we'll use a placeholder or omit it
      const result = await api.validateFullVAT({
        full_vat_number: vatNumber,
        requester_vat: 'BG000000000' // Placeholder for company creation
      });
      
      viesValidation = {
        isValidating: false,
        isValid: result.is_valid,
        companyName: result.company_name,
        companyAddress: result.company_address,
        error: result.is_valid ? null : (result.error_message || 'ДДС номерът не е валиден')
      };
      
      // Auto-fill company name and address if validation successful
      if (result.is_valid) {
        if (result.company_name && !company.name.trim()) {
          company.name = result.company_name;
        }
        if (result.company_address && !company.address.trim()) {
          company.address = result.company_address;
        }
      }
      
    } catch (err) {
      viesValidation = {
        isValidating: false,
        isValid: false,
        companyName: null,
        companyAddress: null,
        error: err instanceof Error ? err.message : 'VIES валидацията се провали'
      };
    }
  }
</script>

<svelte:head>
  <title>Нова фирма - VAT System</title>
</svelte:head>

<div class="max-w-2xl mx-auto">
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
          <span class="text-gray-900">Нова фирма</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">Регистриране на нова фирма</h1>
        <p class="mt-2 text-gray-600">
          Добавяне на задължено лице за ДДС отчетност
        </p>
      </div>
    </div>
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

  <!-- Form -->
  <form on:submit|preventDefault={handleSubmit} class="bg-white rounded-lg shadow-sm">
    <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
      <div class="flex items-center">
        <Building2 class="h-6 w-6 text-blue-600 mr-3" />
        <h3 class="text-lg font-medium text-gray-900">Данни за фирмата</h3>
      </div>
    </div>

    <div class="p-6 space-y-6">
      <!-- EIK (moved first) -->
      <div>
        <label for="uic" class="block text-sm font-medium text-gray-700 mb-2">
          ЕИК (Единен идентификационен код) *
        </label>
        <input
          id="uic"
          type="text"
          bind:value={company.uic}
          on:input={handleUICChange}
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 {validationErrors.uic ? 'border-red-300' : ''}"
          placeholder="123456789"
        />
        {#if validationErrors.uic}
          <p class="mt-1 text-sm text-red-600">{validationErrors.uic}</p>
        {:else}
          <p class="mt-1 text-sm text-gray-500">9-цифрен единен идентификационен код</p>
        {/if}
      </div>

      <!-- Company Name -->
      <div>
        <label for="name" class="block text-sm font-medium text-gray-700 mb-2">
          Наименование на фирмата *
        </label>
        <input
          id="name"
          type="text"
          bind:value={company.name}
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 {validationErrors.name ? 'border-red-300' : ''}"
          placeholder="ООД ПРИМЕРНА ФИРМА"
        />
        {#if validationErrors.name}
          <p class="mt-1 text-sm text-red-600">{validationErrors.name}</p>
        {/if}
      </div>

      <!-- VAT Number with VIES Validation -->
      <div>
        <label for="vat_number" class="block text-sm font-medium text-gray-700 mb-2">
          ДДС номер *
        </label>
        <div class="relative">
          <input
            id="vat_number"
            type="text"
            bind:value={company.vat_number}
            on:blur={validateCompanyVAT}
            class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 {validationErrors.vat_number ? 'border-red-300' : ''}"
            placeholder="BG123456789 или DE123456789"
          />
          
          <!-- VIES Validation Status Icon -->
          {#if viesValidation.isValidating}
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" title="Проверява се в VIES системата..."></div>
            </div>
          {:else if viesValidation.isValid === true}
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
              <svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
            </div>
          {:else if viesValidation.isValid === false}
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
              <svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
              </svg>
            </div>
          {/if}
        </div>
        
        <!-- VIES Validation Result Messages -->
        {#if viesValidation.isValidating}
          <div class="mt-2 text-sm text-blue-600 bg-blue-50 rounded p-2 flex items-center">
            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600 mr-2"></div>
            🌐 Проверява се валидността на ДДС номера в VIES системата на ЕС...
          </div>
        {:else if viesValidation.companyName}
          <div class="mt-2 text-sm text-green-600 bg-green-50 rounded p-2">
            ✓ Валиден ЕС ДДС номер: <strong>{viesValidation.companyName}</strong>
            {#if viesValidation.companyAddress}
              <br>📍 Адрес: {viesValidation.companyAddress}
            {/if}
            <br>
            <button
              type="button"
              on:click={() => {
                if (viesValidation.companyName) company.name = viesValidation.companyName;
                if (viesValidation.companyAddress) company.address = viesValidation.companyAddress;
              }}
              class="mt-2 inline-flex items-center px-3 py-1 border border-transparent text-xs leading-4 font-medium rounded text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              📋 Попълни данните автоматично
            </button>
          </div>
        {/if}
        
        {#if viesValidation.error && viesValidation.isValid !== null}
          <div class="mt-2 text-sm text-amber-600 bg-amber-50 rounded p-2">
            ⓘ {viesValidation.error}
          </div>
        {/if}
        
        {#if validationErrors.vat_number}
          <p class="mt-1 text-sm text-red-600">{validationErrors.vat_number}</p>
        {:else if !viesValidation.companyName && !viesValidation.error}
          <p class="mt-1 text-sm text-gray-500">Започва с "BG" или с код на ЕС държава (например DE, FR)</p>
        {/if}
      </div>

      <!-- Address -->
      <div>
        <label for="address" class="block text-sm font-medium text-gray-700 mb-2">
          Адрес *
        </label>
        <textarea
          id="address"
          bind:value={company.address}
          rows="3"
          class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 {validationErrors.address ? 'border-red-300' : ''}"
          placeholder="гр. София, бул. Витоша 1"
        ></textarea>
        {#if validationErrors.address}
          <p class="mt-1 text-sm text-red-600">{validationErrors.address}</p>
        {/if}
      </div>

      <!-- Active Status -->
      <div class="flex items-center">
        <input
          id="is_active"
          type="checkbox"
          bind:checked={company.is_active}
          class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label for="is_active" class="ml-2 text-sm text-gray-700">
          Активна фирма (може да генерира декларации)
        </label>
      </div>
    </div>

    <!-- Actions -->
    <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
      <a
        href="/companies"
        class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
      >
        Отказ
      </a>
      <button
        type="submit"
        disabled={loading}
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
      >
        {#if loading}
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
          Запазване...
        {:else}
          <Save class="h-4 w-4 mr-2" />
          Запази фирмата
        {/if}
      </button>
    </div>
  </form>

  <!-- Instructions -->
  <div class="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
    <h3 class="text-sm font-medium text-blue-900 mb-2">Важни бележки:</h3>
    <ul class="text-sm text-blue-800 space-y-1">
      <li>• Всички полета маркирани със * са задължителни</li>
      <li>• ЕИК се валидира автоматично спрямо българските стандарти</li>
      <li>• ДДС номерът се генерира автоматично при въвеждане на валиден ЕИК</li>
      <li>• След създаване можете да започнете въвеждане на дневници</li>
    </ul>
  </div>
</div>