
import {candleSeries, volumeSeries, singleWebSocket, addPriceLine} from './tvchart.js';


const currentdir = window.location.pathname.substr(-3, 3).toUpperCase();
const ticker = window.location.pathname.substr(-3, 3).toUpperCase();
const timeframe = document.getElementById('timeframe');
const legend = document.querySelector('.firstrow');
const leverage = document.getElementById('leverage');
const long = document.getElementById('long');
const short = document.getElementById('short');
const availableBalance = document.getElementById('availableassets');
const totalBalanace = document.getElementById('totalassets');
const resetUserAssets = document.getElementById('resetUserAssets');
const orderType = document.getElementById('ordertype');
export const orderPrice = document.getElementById('orderpriceinput');
const customEvent = new Event("change", {"bubbles":true, "cancelable":false});
const orderCost = document.getElementById('ordercost');
const orderValue = document.getElementById('ordervalue');
const orderAmount = document.getElementById('orderamount');
const orderPercent = document.getElementById('orderpercent');
const placeOrder = document.getElementById('placeorder');
const tbodyActive = document.getElementById('tbodyactive');
let currentPrice = document.querySelector('#currentPrice');
const priceLines = {};





// Store trade information and paramaters as JSON to later send to the backend
export const trade = {
  contract: undefined,
  direction: undefined,
  type: 'limit',
  status: 'pending',
  qty: undefined,
  value: undefined,
  open: undefined,
  close: 100000,
  leverage: 1,
  liq: undefined,
  pnl: undefined,
};



// Calculate the PNL on active trades
let pnlObserver = new MutationObserver(function(mutations){
  if (tbodyActive.firstElementChild){
  tbodyActive.querySelectorAll('tr').forEach(
    node => {
      let pnl = ((((+currentPrice.innerHTML/+node.cells[4].innerHTML)-1)*100)* +node.cells[6].getAttribute("value")).toFixed(2);      
      if (node.cells[6].getAttribute("name") === 'Long'){
        pnl >= 0 ? node.cells[6].innerHTML = `<span style="color: green;">${pnl}%</span>` : node.cells[6].innerHTML = `<span style="color: red;">${pnl}%</span>`
      } else {
        pnl <= 0 ? node.cells[6].innerHTML = `<span style="color: green;">${pnl*-1}%</span>` : node.cells[6].innerHTML = `<span style="color: red;">${pnl*-1}%</span>`
      }
    }
  )
}})

pnlObserver.observe(currentPrice, {
  attributes:    true,
  childList:     true,
  characterData: true
})



// User Profile Reset Assets Button
resetUserAssets.addEventListener('click', () => {
  $.ajax({
    url: "/resetassets",
    type: 'GET',
    success: function(response){
      totalBalanace.innerHTML = response.assets;
      availableBalance.innerHTML= response.assets;
      $('#profileModal').modal('hide');
    }
});
})


// Select chart timeframe
timeframe.addEventListener('click', (e) => {
  const name  = e.target.getAttribute('name');
  const data = {};
  data[currentdir] = name;

  legend.innerHTML = legend.innerHTML.replace(/\((.+?)\)/g, "("+name+")");
  $('#loading').show();
  
  // Get historical klines for selected timeframe
  $.ajax({
      url: "/klines",
      data: data,
      type: 'POST',
      success: function(response){candleSeries.setData(response);}
  });

  // Get historical volume for selected timeframe
  $.ajax({
      url: "/volume",
      data: data,
      type: 'POST',
      success: function(response){volumeSeries.setData(response);
          $('#loading').hide();}
  });
  singleWebSocket.acquireWebSocket(currentdir, name);
});

// Display leverage on long/short buttons
leverage.addEventListener('input', () => {
  let currentValue = Number.isInteger(leverage.value*1) ? leverage.value : (leverage.value*1).toFixed(2);
  long.innerHTML = currentValue === '' ? long.innerHTML.replace(/\((.+?)\)/g, "("+`${leverage.placeholder}x`+")"): long.innerHTML.replace(/\((.+?)\)/g, "("+`${currentValue}x`+")");
  short.innerHTML = currentValue === '' ? short.innerHTML.replace(/\((.+?)\)/g, "("+`${leverage.placeholder}x`+")"): short.innerHTML.replace(/\((.+?)\)/g, "("+`${currentValue}x`+")");
  trade.leverage = currentValue;
  if (orderPrice.value !== '' && orderAmount !== ''){
    orderValue.innerHTML = `${parseFloat((orderAmount.value*1)*(leverage.value*1)).toFixed(4)} ${ticker.toUpperCase()}`;
    trade.value = parseFloat((orderAmount.value*1)*(leverage.value*1)).toFixed(4);
  }
});

// Order price change event 
orderPrice.addEventListener("change", () => {
  trade.open = (orderPrice.value*1).toFixed(2);
  if (orderPrice.value !== '' && orderAmount.value !== ''){
  orderAmount.dispatchEvent(customEvent);}
});



// Select order type
orderType.addEventListener('click', ({ target }) => {
  trade.type = target.getAttribute("name");
  target.getAttribute("name") === 'market' ? orderPrice.setAttribute("disabled", true): orderPrice.removeAttribute("disabled");
  if (target.getAttribute("name") === "limit" || target.getAttribute("name") === "conditional" ){
    orderPrice.value = '';}
});

// Order Amount EventListener
orderAmount.addEventListener("change", () => {
  (((orderAmount.value*1)*(orderPrice.value*1))>availableBalance.innerHTML*1) ? orderAmount.classList.add('is-invalid') :  orderAmount.classList.remove('is-invalid');
  if (orderPrice.value !== ''){
    orderCost.innerHTML = `$${parseFloat((orderAmount.value*1)*(orderPrice.value*1)).toFixed(2)}`;
    orderValue.innerHTML = `${parseFloat((orderAmount.value*1)*(leverage.value*1)).toFixed(4)} ${ticker}`;
    trade.qty = parseFloat((orderAmount.value*1)).toFixed(4);}
    trade.value = parseFloat((orderAmount.value*1)*(leverage.value*1)).toFixed(4);
})

// Calculate order amount
orderPercent.addEventListener('click', (e) => {
  if (orderPrice.value === ''){
    return
  } else {
    orderAmount.value = (((e.target.value*1)*(availableBalance.innerHTML*1))/(orderPrice.value*1)).toFixed(4);
    orderAmount.dispatchEvent(customEvent); }
  });
  
  


// Open confirmation modal if all criterions are satified when clicking long or short button
long.addEventListener('click', ()=> {
  if (orderPrice.value !== '' && orderAmount.value !== '' & !orderAmount.classList.contains('is-invalid')){
    loadConfirmationModal('Long');
  } 
});

// Open confirmation modal if all criterions are satified when clicking long or short button
short.addEventListener('click', () => {
  if (orderPrice.value !== '' && orderAmount.value !== '' & !orderAmount.classList.contains('is-invalid')){
    loadConfirmationModal('Short');
  } 
});


// Execute Order: AJAX Post request to backend on trade confirmation
placeOrder.addEventListener('click', () => {
  if (trade.type == 'market') { 
    trade.status = 'active';
  } else {
    let returnStatus = verifyTradeStatus(trade.direction, trade.open);
    if (returnStatus == 'active'){trade.open = +currentPrice.innerHTML}
  }
  
  $.ajax({
    url: "/loadtrade",
    data: trade,
    type: 'POST',
    success: function (response){
      availableBalance.innerHTML = response.available;
      $('#tradeconfirmation').modal('hide');
      $('#ordersuccess').removeClass('d-none');
      $("#ordersuccess").fadeTo(2000, 500).slideUp(500, function(){$("#ordersuccess").slideUp(500);});}
  });

});


// https://www.bybit.com/en-US/help-center/apex/bybitHC_Article/?id=000001067
function calculateLiquidation(type){
  const MMR = ticker === 'BTC' ? 0.005: 0.01;
  const IMR = 1/(leverage.value*1);
  const liquidationPrice = type === 'Long' ? (orderPrice.value*1)*(1-IMR+MMR): (orderPrice.value*1)*(1+IMR-MMR);
  trade.liq = parseFloat(liquidationPrice).toFixed(2);
  return parseFloat(liquidationPrice).toFixed(2)
};


// Display the Order confirmation Modal
function loadConfirmationModal(type){
  trade.contract = `${ticker}USDT`;
  trade.direction = type;  
  const valueItems = [`${ticker}USDT`, `${type} ${leverage.value}x`, orderPrice.value, `${orderAmount.value} ${ticker}`, orderValue.innerHTML, 
                      orderCost.innerHTML, `$${calculateLiquidation(type)}`];
  for (let i=0; i < valueItems.length; i++){
    Array.from(document.getElementsByClassName('lival'))[i].innerHTML = valueItems[i];
  };
  $('#tradeconfirmation').modal('show');
};



// Run the following on page load
$(document).ready(function(){
  $('.tooltips').tooltip({trigger : 'hover'})
    const trPositions = [...document.querySelectorAll('.trposition')];
    if (trPositions.length != 0){
      trPositions.forEach((x,i) => {
      priceLines[x.id] = addPriceLine(x) 
    })
    }  

    
    const socket = io.connect("http://127.0.0.1:5000")

    socket.on('newTrade',function(msg) {
      let newTR  =  newTableRow(msg);
      priceLines[newTR.id] = addPriceLine(newTR);
    })

    socket.on('updateTrade',function(msg) {
      let updatedTR = updateTableRow(msg);
      candleSeries.removePriceLine(priceLines[msg.id])
      priceLines[msg.id] = addPriceLine(updatedTR);
    })

    socket.on('closeTrade', function(msg){
      document.getElementById(`${msg.id}`).remove()
      candleSeries.removePriceLine(priceLines[msg.id])
      delete priceLines[msg.id];
      $(`.tt${msg.id}`).tooltip('hide');
      if (msg.status === 'liquidated'){
        $('#liquidated').html(`Position #${msg.id} liquidated!`)
        $('#liquidated').removeClass('d-none');
        $('#liquidated').fadeTo(2000, 500).slideUp(500, function(){$("#liquidated").slideUp(500);});
      } else {
        $('#promoted').html(`Position #${msg.id} is now active!`)
        $('#promoted').removeClass('d-none');
        $('#promoted').fadeTo(2000, 500).slideUp(500, function(){$("#promoted").slideUp(500);});   
      }
    })

    $('#loading').show();  //Loading animation
    const init = {};
    init[currentdir]='15m'
    // Get historical Kline data
    $.ajax({
        url: "/klines",
        data: init,
        type: 'POST',
        success: function (response){candleSeries.setData(response);},
    })
    // Get historical Volume data
    $.ajax({
        url: "/volume",
        data: init,
        type: 'POST',
        success: function (response){volumeSeries.setData(response);
            $('#loading').hide();
        },
    })
    singleWebSocket.acquireWebSocket(currentdir, init[currentdir]); // Acquire websocket for real-time asset prices (client)
});

//Manually closing trades 
function closeTrade(e){
  const trID = e.parentNode.parentNode.id;
  const trStatus = e.parentNode.parentNode.getAttribute("name");
  $(`.tt${trID}`).tooltip('hide');
  candleSeries.removePriceLine(priceLines[trID])
  delete priceLines[trID];
  let pnl = trStatus === 'active' ? e.parentNode.previousElementSibling.firstChild.innerHTML.slice(0,-1) : 0
  e.parentNode.parentNode.remove();
  $.ajax({
    url: "/closetrade",
    data: {'id': trID, 'status': trStatus, 'contract':`${currentdir}USDT` , 'pnl':`${pnl}`},
    type: 'POST',
    success: function (response){
      $('#closed').html(`Position #${trID} closed!`)
      $('#closed').removeClass('d-none');
      $('#closed').fadeTo(2000, 500).slideUp(500, function(){$("#closed").slideUp(500);});
      availableBalance.innerHTML= (parseFloat(availableBalance.innerHTML)+ parseFloat(response.available)).toFixed(2);
      totalBalanace.innerHTML = (parseFloat(totalBalanace.innerHTML)+ parseFloat(response.total)).toFixed(2);
    },
})
}

window.closeTrade = closeTrade

// Add a new table row position
function newTableRow(position){
  document.getElementById(`tbody${position.status}`).innerHTML += `
  <tr style="font-size: .9rem;" id="${position.id}" class="trposition" name="${position.status}">
    <th style="padding-left: 16px;" scope="row" class ="${position.direction}">${position.contract} (${position.direction} ${position.leverage}x)</th>
    <td class="posID">#${position.id}</td>
    <td>${position.qty}</td>
    <td>${position.value}</td>
    <td class="posOpen">${position.open}</td>
    <td class="posLiq">${position.liq}</td>
    <td name="${position.direction}" value="${position.leverage}">-</td>
    <td style="border-top:0px"><a onclick="closeTrade(this)" href="#"  class="tooltips tt${position.id}" data-placement="top" title="Close Trade?"><img class="closebtn" style="height:1.25em; padding-left:5px"  src="../static/images/svgclosebtn.svg" alt=""></a></td>
    </tr>`;
    $(`.tt${position.id}`).tooltip({trigger : 'hover'})


    return document.getElementById(`${position.id}`)
}


// Update active and pending trades
function updateTableRow(position){

  document.getElementById(`${position.id}`).innerHTML = `
    <th style="padding-left: 16px;" scope="row" class ="${position.direction}">${position.contract} (${position.direction} ${position.leverage}x)</th>
    <td class="posID">#${position.id}</td>
    <td>${position.qty}</td>
    <td>${position.value}</td>
    <td class="posOpen">${position.open}</td>
    <td class="posLiq">${position.liq}</td>
    <td name="${position.direction}" value="${position.leverage}">-</td>
    <td style="border-top:0px"><a onclick="closeTrade(this)" href="#" class="tooltips tt${position.id}" data-placement="top" title="Close Trade?"><img class="closebtn" style="height:1.25em; padding-left:5px"  src="../static/images/svgclosebtn.svg" alt=""></a></td>`;
    $(`.tt${position.id}`).tooltip({trigger : 'hover'})
    return document.getElementById(`${position.id}`);
  }


// Before submitting the Trade request, verify if the order should be a market or limit order
function verifyTradeStatus(direction, open){
  if (direction == 'Long') {
    (open*1)>=(+currentPrice.innerHTML*1) ? trade.status = 'active' : trade.status = 'pending'
  }
  else { 
    (open*1)<=(+currentPrice.innerHTML*1) ? trade.status = 'active' : trade.status = 'pending'
}
return trade.status
}





