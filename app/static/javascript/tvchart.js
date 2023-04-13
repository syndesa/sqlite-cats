import { orderPrice } from "./tradeui.js";

const chart = document.querySelector('.chart');
const chartClickEvent = new Event("change", {"bubbles":true, "cancelable":false});


// Singleton class (limits the websocket connection to one & switches to another socket when required )
class WebSocketManager{
	constructor(){
	  if (WebSocketManager._instance){
		throw new Error("Instance already exists!")
	  }
	  WebSocketManager._instance = this;
	  this.binanceSocket = null;
	}
	
	  acquireWebSocket(asset, time){
		if (!(this.binanceSocket instanceof WebSocket)){
		  this.binanceSocket = new WebSocket(`wss://stream.binance.com:9443/ws/${asset.toLowerCase()}usdt@kline_${time.toLowerCase()}`);
		  this.onMessageConfig(this.binanceSocket);
		  return this.binanceSocket;
		} else {
		  this.releaseWebSocket(this.binanceSocket);
		  this.binanceSocket = new WebSocket(`wss://stream.binance.com:9443/ws/${asset.toLowerCase()}usdt@kline_${time.toLowerCase()}`);
		  this.onMessageConfig(this.binanceSocket);
		  return this.binanceSocket;
		}
	  }
	
	  releaseWebSocket(socket){
		socket.close();
		this.binanceSocket = null; 
	  }
  
	  onMessageConfig(socket){
		socket.onmessage = function (event) {
		  const candlestick = {
			"time": JSON.parse(event.data).k.t/1000,
			"open": JSON.parse(event.data).k.o,
			"high": JSON.parse(event.data).k.h,
			"low": JSON.parse(event.data).k.l,
			"close": JSON.parse(event.data).k.c,
			  }
		  const volume = {
			"value": JSON.parse(event.data).k.v,
			"time": JSON.parse(event.data).k.t/1000,
			  }
		  
			candleSeries.update(candlestick);
			volumeSeries.update(volume);
			const marketLabel = document.getElementById("market")
			document.querySelector('#currentPrice').innerHTML = Number(candlestick.close).toFixed(2);
			// $('#currentPrice').firstChild.data = Number(candlestick.close).toFixed(2);
			if (marketLabel.classList.contains('active')){
				document.getElementById('orderpriceinput').value = Number(candlestick.close).toFixed(2);
			} 
		  }
	  }
	  
  }
  
  const singleWebSocket = new WebSocketManager()
  

// Initialize the chart and configure 
var lightChart = LightweightCharts.createChart(chart, {
	layout: {
		backgroundColor: '#e3e2e2',
		textColor: 'rgba(0,0,0,1)',
	},
	grid: {
		vertLines: {
			color: 'rgba(197, 203, 206, 0.7)',
		},
		horzLines: {
			color: 'rgba(197, 203, 206, 0.7)',
		},
	},
	crosshair: {
		mode: LightweightCharts.CrosshairMode.Normal,
	},
	rightPriceScale: {
		borderColor: 'rgba(0, 0, 0, 1)',
		scaleMargins: {
			top: 0.1,
			bottom: 0.3,
		},
		borderVisible: false,
		
	},
	timeScale: {
		borderColor: 'rgba(0, 0, 0, 1)',
	},
});




// Candlestick series chart config
const candleSeries = lightChart.addCandlestickSeries({
	upColor: '#098205',
	downColor: '#e31000',
	borderDownColor: '#e31000',
	borderUpColor: '#098205',
	wickDownColor: '#000000',
	wickUpColor: '#000000',
});

// Volume series chart config
const volumeSeries = lightChart.addHistogramSeries({
	color: '#26a69a',
	priceFormat: {
		type: 'volume',
	},
	priceScaleId: '', // set as an overlay by setting a blank priceScaleId
					  // set the positioning of the volume series
	scaleMargins: {
		top: 0.95, // highest point of the series will be 70% away from the top
		bottom: 0,
	},
});


export {candleSeries, volumeSeries, singleWebSocket}



// Get on click coordinate price from chart & assign to order price value
lightChart.subscribeClick(param => {
	const cursorPrice = candleSeries.coordinateToPrice(param.point.y)
	if (document.getElementById('market').classList.contains('active')){
		return
	} else {
		orderPrice.value = cursorPrice.toFixed(2);
		orderPrice.dispatchEvent(chartClickEvent);
	}
})


// Add a priceLine to the Chart (i.e. Liquidations/Open prices)
export function addPriceLine(row){
	const status = row.getAttribute("name");
	const params = {
		price: status === 'active'? parseFloat(row.cells[5].innerHTML): parseFloat(row.cells[4].innerHTML),
		color: status === 'active' ? 'rgba(255, 193, 7, 1)' : 'rgba(12, 201, 223, 1)',
		lineWidth: 2,
		lineStyle: LightweightCharts.LineStyle.Dotted,
		title: status === 'active' ? `${row.cells[1].innerHTML} L`: `${row.cells[1].innerHTML} B`,
		}
		return candleSeries.createPriceLine(params)
}



//  // Make Chart Responsive with screen resize
 new ResizeObserver(entries => {
	if (entries.length === 0 || entries[0].target !== chart) { return; }
	const newRect = entries[0].contentRect;
	lightChart.applyOptions({ height: newRect.height, width: newRect.width });
  }).observe(chart);


